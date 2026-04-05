from __future__ import annotations

from collections import deque

from app.llm.base import LLMRequest, LLMResponse


class FakeLLMClient:
    def __init__(self, responses: list[LLMResponse]):
        self._responses = deque(responses)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._responses:
            return LLMResponse(content="No more scripted responses", tool_calls=[], finish_reason="stop", usage={})
        return self._responses.popleft()
