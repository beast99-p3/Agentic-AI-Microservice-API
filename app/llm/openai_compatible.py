from __future__ import annotations

import json
from typing import Any, cast

from openai import AsyncOpenAI
from openai._types import NOT_GIVEN

from app.llm.base import LLMRequest, LLMResponse, LLMToolCall


class OpenAICompatibleClient:
    def __init__(self, api_key: str, base_url: str | None = None):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        tools_payload: Any = (
            [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in request.tools
            ]
            if request.tools
            else NOT_GIVEN
        )

        response = await self._client.chat.completions.create(
            model=request.model,
            temperature=request.temperature,
            messages=cast(Any, request.messages),
            tools=tools_payload,
            timeout=request.timeout_seconds,
        )

        choice = response.choices[0]
        message = choice.message

        calls: list[LLMToolCall] = []
        for call in message.tool_calls or []:
            calls.append(
                LLMToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments_json=call.function.arguments,
                )
            )

        usage = {
            "prompt_tokens": int(response.usage.prompt_tokens) if response.usage else 0,
            "completion_tokens": int(response.usage.completion_tokens) if response.usage else 0,
            "total_tokens": int(response.usage.total_tokens) if response.usage else 0,
        }

        content = message.content or ""
        if isinstance(content, list):
            content = json.dumps(content)

        return LLMResponse(
            content=str(content).strip(),
            tool_calls=calls,
            finish_reason=str(choice.finish_reason or "unknown"),
            usage=usage,
        )
