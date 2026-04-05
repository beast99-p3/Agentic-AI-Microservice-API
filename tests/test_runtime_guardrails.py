from __future__ import annotations

from collections.abc import Callable

import pytest

from app.agents.runtime import AgentRuntime
from app.core.config import Settings
from app.llm.base import LLMResponse, LLMToolCall
from app.schemas.events import TerminationReason
from app.schemas.requests import AgentRunRequest
from app.tools.registry import ToolRegistry
from app.tools.safe_math import SafeMathTool
from app.tools.text_utils import TextUtilsTool
from tests.fakes import FakeLLMClient


@pytest.mark.asyncio
async def test_agent_terminates_on_step_limit(
    llm_response_factory: Callable[..., LLMResponse],
) -> None:
    llm = FakeLLMClient(
        responses=[
            llm_response_factory(tool_calls=[LLMToolCall(id="1", name="safe_math", arguments_json='{"expression":"1+1"}')]),
            llm_response_factory(tool_calls=[LLMToolCall(id="2", name="safe_math", arguments_json='{"expression":"2+2"}')]),
        ]
    )
    settings = Settings(LLM_API_KEY="dummy", REPEATED_TOOL_CALL_THRESHOLD=999)
    runtime = AgentRuntime(settings=settings, llm_client=llm, tool_registry=ToolRegistry([SafeMathTool()]))

    result = await runtime.run(AgentRunRequest(task="Compute", max_steps=1, max_tool_calls=5))
    assert result.termination_reason == TerminationReason.STEP_LIMIT


@pytest.mark.asyncio
async def test_repeated_tool_call_guardrail(
    llm_response_factory: Callable[..., LLMResponse],
) -> None:
    repeated = LLMToolCall(id="1", name="safe_math", arguments_json='{"expression":"3*3"}')
    llm = FakeLLMClient(
        responses=[
            llm_response_factory(tool_calls=[repeated]),
            llm_response_factory(tool_calls=[repeated]),
            llm_response_factory(tool_calls=[repeated]),
        ]
    )
    settings = Settings(LLM_API_KEY="dummy", REPEATED_TOOL_CALL_THRESHOLD=1)
    runtime = AgentRuntime(settings=settings, llm_client=llm, tool_registry=ToolRegistry([SafeMathTool()]))

    result = await runtime.run(AgentRunRequest(task="Compute", max_steps=5, max_tool_calls=10))
    assert result.termination_reason == TerminationReason.REPEATED_BEHAVIOR


@pytest.mark.asyncio
async def test_disallowed_tool_access(
    llm_response_factory: Callable[..., LLMResponse],
) -> None:
    llm = FakeLLMClient(
        responses=[
            llm_response_factory(
                tool_calls=[LLMToolCall(id="1", name="safe_math", arguments_json='{"expression":"9+1"}')]
            )
        ]
    )
    settings = Settings(LLM_API_KEY="dummy", REPEATED_TOOL_CALL_THRESHOLD=10)
    runtime = AgentRuntime(
        settings=settings,
        llm_client=llm,
        tool_registry=ToolRegistry([SafeMathTool(), TextUtilsTool()]),
    )

    result = await runtime.run(
        AgentRunRequest(task="Compute", allowed_tools=["text_utils"], max_steps=3, max_tool_calls=3)
    )
    assert result.termination_reason == TerminationReason.DISALLOWED_TOOL
