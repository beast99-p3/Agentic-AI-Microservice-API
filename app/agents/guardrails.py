from __future__ import annotations

import time
from collections import Counter
from typing import Counter as TypingCounter

from app.schemas.events import GuardrailEvent, TerminationReason


class GuardrailManager:
    def __init__(
        self,
        max_steps: int,
        max_tool_calls: int,
        max_runtime_seconds: int,
        repeated_tool_call_threshold: int,
    ):
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.max_runtime_seconds = max_runtime_seconds
        self.repeated_tool_call_threshold = repeated_tool_call_threshold
        self.start_time = time.perf_counter()
        self._tool_fingerprints: TypingCounter[str] = Counter()

    def elapsed_seconds(self) -> float:
        return time.perf_counter() - self.start_time

    def check_runtime_limit(self) -> GuardrailEvent | None:
        if self.elapsed_seconds() > self.max_runtime_seconds:
            return GuardrailEvent(
                code="runtime_limit",
                message="Max runtime exceeded.",
            )
        return None

    def check_step_limit(self, step_index: int) -> GuardrailEvent | None:
        if step_index > self.max_steps:
            return GuardrailEvent(
                code="step_limit",
                message="Max steps exceeded.",
                step=step_index,
            )
        return None

    def check_tool_call_limit(self, current_tool_calls: int) -> GuardrailEvent | None:
        if current_tool_calls > self.max_tool_calls:
            return GuardrailEvent(
                code="tool_call_limit",
                message="Max tool calls exceeded.",
            )
        return None

    def detect_repeated_tool_call(self, fingerprint: str, step: int) -> GuardrailEvent | None:
        self._tool_fingerprints[fingerprint] += 1
        if self._tool_fingerprints[fingerprint] > self.repeated_tool_call_threshold:
            return GuardrailEvent(
                code="repeated_tool_call",
                message="Repeated identical tool call detected.",
                step=step,
            )
        return None


def warning_to_termination(event: GuardrailEvent) -> TerminationReason:
    mapping = {
        "runtime_limit": TerminationReason.RUNTIME_LIMIT,
        "step_limit": TerminationReason.STEP_LIMIT,
        "tool_call_limit": TerminationReason.TOOL_CALL_LIMIT,
        "repeated_tool_call": TerminationReason.REPEATED_BEHAVIOR,
        "disallowed_tool": TerminationReason.DISALLOWED_TOOL,
        "invalid_tool_arguments": TerminationReason.INVALID_TOOL_ARGUMENTS,
        "safety_trigger": TerminationReason.SAFETY_TRIGGER,
    }
    return mapping.get(event.code, TerminationReason.ERROR)
