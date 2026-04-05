from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.events import AgentEvent, BudgetUsage, GuardrailEvent, TerminationReason, ToolCallRecord


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str


class ToolDescriptor(BaseModel):
    name: str
    description: str
    args_schema: dict[str, Any]


class ToolsResponse(BaseModel):
    tools: list[ToolDescriptor]


class AgentRunResponse(BaseModel):
    request_id: str
    final_answer: str
    termination_reason: TerminationReason
    warnings: list[GuardrailEvent] = Field(default_factory=lambda: [])
    tool_calls: list[ToolCallRecord] = Field(default_factory=lambda: [])
    step_trace: list[AgentEvent] = Field(default_factory=lambda: [])
    budget_usage: BudgetUsage


class PromptPreviewResponse(BaseModel):
    composed_system_prompt: str
    user_task: str
    runtime_settings: dict[str, Any]
    available_tools: list[str]


class ErrorResponse(BaseModel):
    detail: str
    request_id: str | None = None
    timestamp: datetime
