from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Protocol


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(slots=True)
class LLMToolCall:
    id: str
    name: str
    arguments_json: str


@dataclass(slots=True)
class LLMResponse:
    content: str
    tool_calls: list[LLMToolCall]
    finish_reason: str
    usage: dict[str, int]


@dataclass(slots=True)
class LLMRequest:
    messages: list[dict[str, str]]
    tools: list[ToolSpec]
    model: str
    temperature: float
    timeout_seconds: int


class BaseLLMClient(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError
