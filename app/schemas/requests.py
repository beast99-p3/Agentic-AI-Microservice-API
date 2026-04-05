from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentRunRequest(BaseModel):
    task: str = Field(..., min_length=3, max_length=8000)
    system_prompt_override: str | None = Field(default=None, max_length=8000)
    max_steps: int = Field(default=8, ge=1, le=30)
    max_tool_calls: int = Field(default=12, ge=0, le=60)
    max_runtime_seconds: int = Field(default=45, ge=3, le=300)
    allowed_tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    require_confirmation_for: list[str] | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.5)

    @field_validator("allowed_tools")
    @classmethod
    def validate_allowed_tools(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("allowed_tools must not contain duplicates")
        return cleaned

    @field_validator("require_confirmation_for")
    @classmethod
    def validate_confirmations(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("require_confirmation_for must not contain duplicates")
        return cleaned


class PromptPreviewRequest(BaseModel):
    task: str = Field(..., min_length=3, max_length=8000)
    system_prompt_override: str | None = Field(default=None, max_length=8000)
    allowed_tools: list[str] = Field(default_factory=list)
    max_steps: int = Field(default=8, ge=1, le=30)
    max_tool_calls: int = Field(default=12, ge=0, le=60)
    max_runtime_seconds: int = Field(default=45, ge=3, le=300)


class AgentStreamRequest(AgentRunRequest):
    pass
