from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from app.agents.guardrails import GuardrailManager, warning_to_termination
from app.agents.planner import Planner
from app.agents.prompts import compose_system_prompt
from app.agents.state import RuntimeResult, RuntimeState
from app.core.config import Settings
from app.core.security import looks_like_prompt_injection
from app.llm.base import BaseLLMClient, LLMRequest, ToolSpec
from app.schemas.events import AgentEvent, BudgetUsage, EventType, GuardrailEvent, TerminationReason, ToolCallRecord
from app.schemas.requests import AgentRunRequest
from app.tools.base import ToolExecutionError, ToolValidationError
from app.tools.registry import ToolRegistry

EventHandler = Callable[[AgentEvent], Awaitable[None] | None]


class AgentRuntime:
    """Runs a steerable tool-using agent loop with strict runtime guardrails.

    The loop is intentionally conservative: it enforces hard budgets, tracks
    repeated behavior, sanitizes tool outputs, and captures a full step trace
    for observability and post-run debugging.
    """

    def __init__(self, settings: Settings, llm_client: BaseLLMClient, tool_registry: ToolRegistry):
        self.settings = settings
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.planner = Planner()
        self.logger = logging.getLogger("agent.runtime")

    async def run(self, request: AgentRunRequest, event_handler: EventHandler | None = None) -> RuntimeResult:
        request_id = str(uuid.uuid4())
        state = RuntimeState(request_id=request_id, task=request.task)

        max_steps = request.max_steps or self.settings.default_max_steps
        max_tool_calls = request.max_tool_calls or self.settings.default_max_tool_calls
        max_runtime_seconds = request.max_runtime_seconds or self.settings.default_max_runtime_seconds

        allowlist = set(request.allowed_tools) if request.allowed_tools else None

        guardrails = GuardrailManager(
            max_steps=max_steps,
            max_tool_calls=max_tool_calls,
            max_runtime_seconds=max_runtime_seconds,
            repeated_tool_call_threshold=self.settings.repeated_tool_call_threshold,
        )

        system_prompt = compose_system_prompt(
            system_prompt_override=request.system_prompt_override,
            max_steps=max_steps,
            max_tool_calls=max_tool_calls,
            max_runtime_seconds=max_runtime_seconds,
        )
        planning_hint = self.planner.build_planning_hint(request.task)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.task},
            {"role": "system", "content": planning_hint},
        ]

        await self._emit(
            state,
            AgentEvent(type=EventType.STARTED, message="Agent run started", data={"request_id": request_id}),
            event_handler,
        )

        for step in range(1, max_steps + 1):
            state.steps_used = step

            limit_warning = guardrails.check_runtime_limit()
            if limit_warning:
                return await self._terminate(state, guardrails, warning_to_termination(limit_warning), limit_warning, event_handler)

            await self._emit(
                state,
                AgentEvent(type=EventType.STEP_STARTED, step=step, message=f"Starting step {step}"),
                event_handler,
            )

            specs = [
                ToolSpec(name=item["name"], description=item["description"], parameters=item["parameters"])
                for item in self.tool_registry.function_specs(allowlist)
            ]

            llm_request = LLMRequest(
                messages=messages,
                tools=specs,
                model=request.model or self.settings.llm_default_model,
                temperature=request.temperature if request.temperature is not None else self.settings.llm_default_temperature,
                timeout_seconds=self.settings.llm_timeout_seconds,
            )

            try:
                llm_response = await self.llm_client.complete(llm_request)
            except Exception as exc:
                warning, reason, fallback = self._classify_llm_exception(exc, step)
                if fallback:
                    state.final_answer = fallback
                return await self._terminate(state, guardrails, reason, warning, event_handler)

            state.prompt_tokens += llm_response.usage.get("prompt_tokens", 0)
            state.completion_tokens += llm_response.usage.get("completion_tokens", 0)

            await self._emit(
                state,
                AgentEvent(
                    type=EventType.MODEL_RESPONSE,
                    step=step,
                    message="Model produced a response",
                    data={
                        "finish_reason": llm_response.finish_reason,
                        "tool_calls": len(llm_response.tool_calls),
                        "content_preview": llm_response.content[:400],
                    },
                ),
                event_handler,
            )

            if not llm_response.tool_calls:
                content = llm_response.content.strip()
                if not content:
                    warning = GuardrailEvent(
                        code="empty_response",
                        message="Model returned empty content without tool calls.",
                        step=step,
                    )
                    return await self._terminate(state, guardrails, TerminationReason.ERROR, warning, event_handler)

                state.final_answer = content
                reason = TerminationReason.REFUSED if "cannot" in content.lower() and "help" in content.lower() else TerminationReason.COMPLETED
                return await self._terminate(state, guardrails, reason, None, event_handler)

            messages.append({"role": "assistant", "content": llm_response.content or "", "tool_calls": "present"})

            for tool_call in llm_response.tool_calls:
                state.tool_calls_used += 1

                tool_limit_warning = guardrails.check_tool_call_limit(state.tool_calls_used)
                if tool_limit_warning:
                    return await self._terminate(state, guardrails, warning_to_termination(tool_limit_warning), tool_limit_warning, event_handler)

                fingerprint = f"{tool_call.name}:{tool_call.arguments_json}"
                repeat_warning = guardrails.detect_repeated_tool_call(fingerprint, step)
                if repeat_warning:
                    return await self._terminate(state, guardrails, warning_to_termination(repeat_warning), repeat_warning, event_handler)

                if allowlist and tool_call.name not in allowlist:
                    warning = GuardrailEvent(
                        code="disallowed_tool",
                        message=f"Tool '{tool_call.name}' is not allowed for this request.",
                        step=step,
                    )
                    return await self._terminate(state, guardrails, TerminationReason.DISALLOWED_TOOL, warning, event_handler)

                if request.require_confirmation_for and tool_call.name in request.require_confirmation_for:
                    warning = GuardrailEvent(
                        code="confirmation_required",
                        message=f"Tool '{tool_call.name}' requires confirmation and was blocked.",
                        step=step,
                    )
                    return await self._terminate(state, guardrails, TerminationReason.SAFETY_TRIGGER, warning, event_handler)

                await self._emit(
                    state,
                    AgentEvent(
                        type=EventType.TOOL_CALL,
                        step=step,
                        message=f"Calling tool {tool_call.name}",
                        data={"tool": tool_call.name, "args": tool_call.arguments_json[:400]},
                    ),
                    event_handler,
                )

                started = time.perf_counter()
                try:
                    tool_output, meta = await self.tool_registry.execute(
                        tool_name=tool_call.name,
                        raw_arguments=tool_call.arguments_json,
                        timeout_seconds=self.settings.tool_timeout_seconds,
                        allowlist=allowlist,
                    )
                except asyncio.TimeoutError:
                    warning = GuardrailEvent(
                        code="tool_timeout",
                        message=f"Tool '{tool_call.name}' timed out.",
                        step=step,
                    )
                    return await self._terminate(state, guardrails, TerminationReason.SAFETY_TRIGGER, warning, event_handler)
                except ToolValidationError as exc:
                    warning = GuardrailEvent(
                        code="invalid_tool_arguments",
                        message=f"Invalid arguments for tool '{tool_call.name}': {exc}",
                        step=step,
                    )
                    return await self._terminate(state, guardrails, TerminationReason.INVALID_TOOL_ARGUMENTS, warning, event_handler)
                except ToolExecutionError as exc:
                    warning = GuardrailEvent(
                        code="tool_execution_error",
                        message=f"Tool '{tool_call.name}' failed: {exc}",
                        step=step,
                    )
                    return await self._terminate(state, guardrails, TerminationReason.ERROR, warning, event_handler)

                duration_ms = int((time.perf_counter() - started) * 1000)

                if looks_like_prompt_injection(tool_output):
                    state.warnings.append(
                        GuardrailEvent(
                            code="prompt_injection_signal",
                            message="Potential prompt injection pattern detected in tool output.",
                            step=step,
                        )
                    )

                state.tool_calls.append(
                    ToolCallRecord(
                        name=tool_call.name,
                        arguments=meta.get("args", {}),
                        status="ok",
                        output_preview=tool_output[:300],
                        duration_ms=duration_ms,
                    )
                )

                wrapped_tool_output = (
                    "TOOL OUTPUT (UNTRUSTED DATA):\n"
                    f"tool={tool_call.name}\n"
                    f"data={tool_output}"
                )

                messages.append({"role": "tool", "name": tool_call.name, "content": wrapped_tool_output})

                await self._emit(
                    state,
                    AgentEvent(
                        type=EventType.TOOL_RESULT,
                        step=step,
                        message=f"Tool {tool_call.name} completed",
                        data={
                            "tool": tool_call.name,
                            "duration_ms": duration_ms,
                            "output_preview": tool_output[:300],
                        },
                    ),
                    event_handler,
                )

        warning = GuardrailEvent(code="step_limit", message="Reached maximum step budget.", step=max_steps)
        return await self._terminate(state, guardrails, TerminationReason.STEP_LIMIT, warning, event_handler)

    def _classify_llm_exception(
        self,
        exc: Exception,
        step: int,
    ) -> tuple[GuardrailEvent, TerminationReason, str | None]:
        text = str(exc)
        lowered = text.lower()

        is_rate_limited = (
            "429" in text
            or "resource_exhausted" in lowered
            or "quota" in lowered
            or "rate limit" in lowered
        )

        if is_rate_limited:
            retry_after = self._extract_retry_after_seconds(text)
            retry_hint = (
                f" Retry after about {retry_after} seconds."
                if retry_after is not None
                else " Retry after a short delay or increase provider quota."
            )

            warning = GuardrailEvent(
                code="llm_rate_limited",
                message="LLM provider quota or rate limit exceeded." + retry_hint,
                step=step,
            )

            fallback = (
                "The request is valid, but the configured LLM provider rejected it due to quota/rate limits."
                + retry_hint
                + " You can retry later, switch to another model, or use a key/project with available quota."
            )
            return warning, TerminationReason.RATE_LIMIT, fallback

        short = text.replace("\n", " ").strip()
        if len(short) > 320:
            short = short[:320] + "..."

        warning = GuardrailEvent(code="llm_error", message=f"LLM call failed: {short}", step=step)
        return warning, TerminationReason.ERROR, None

    @staticmethod
    def _extract_retry_after_seconds(error_text: str) -> int | None:
        patterns = [
            r"retry in\s+([0-9]+(?:\.[0-9]+)?)s",
            r"retryDelay['\"]?\s*:\s*['\"]([0-9]+)s",
        ]
        for pattern in patterns:
            match = re.search(pattern, error_text, flags=re.IGNORECASE)
            if match:
                try:
                    return int(float(match.group(1)))
                except ValueError:
                    return None
        return None

    async def _emit(self, state: RuntimeState, event: AgentEvent, event_handler: EventHandler | None) -> None:
        state.trace.append(event)
        self.logger.info(event.message, extra={"request_id": state.request_id, "event": event.type.value})
        if event_handler:
            maybe = event_handler(event)
            if asyncio.iscoroutine(maybe):
                await maybe

    async def _terminate(
        self,
        state: RuntimeState,
        guardrails: GuardrailManager,
        reason: TerminationReason,
        warning: GuardrailEvent | None,
        event_handler: EventHandler | None,
    ) -> RuntimeResult:
        if warning:
            state.warnings.append(warning)
            await self._emit(
                state,
                AgentEvent(
                    type=EventType.GUARDRAIL_WARNING,
                    step=warning.step,
                    message=warning.message,
                    data={"code": warning.code},
                ),
                event_handler,
            )

        state.termination_reason = reason

        await self._emit(
            state,
            AgentEvent(
                type=EventType.TERMINATED,
                message="Agent run terminated",
                data={"termination_reason": reason.value},
            ),
            event_handler,
        )

        return RuntimeResult(
            request_id=state.request_id,
            final_answer=state.final_answer,
            termination_reason=reason,
            warnings=state.warnings,
            step_trace=state.trace,
            tool_calls=state.tool_calls,
            budget_usage=BudgetUsage(
                steps_used=state.steps_used,
                steps_limit=guardrails.max_steps,
                tool_calls_used=state.tool_calls_used,
                tool_calls_limit=guardrails.max_tool_calls,
                runtime_seconds=round(guardrails.elapsed_seconds(), 3),
                runtime_limit_seconds=guardrails.max_runtime_seconds,
                estimated_input_tokens=state.prompt_tokens,
                estimated_output_tokens=state.completion_tokens,
            ),
            metadata={},
        )
