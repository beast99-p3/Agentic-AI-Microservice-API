from __future__ import annotations

import pytest

from app.llm.base import LLMResponse, LLMToolCall


@pytest.fixture
def llm_response_factory():
    def _build(content: str = "", tool_calls: list[LLMToolCall] | None = None) -> LLMResponse:
        return LLMResponse(
            content=content,
            tool_calls=tool_calls or [],
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

    return _build
