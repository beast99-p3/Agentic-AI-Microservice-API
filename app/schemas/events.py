from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TerminationReason(str, Enum):
    COMPLETED = "completed"
    REFUSED = "refused"
    RATE_LIMIT = "rate_limit"
    STEP_LIMIT = "step_limit"
    TOOL_CALL_LIMIT = "tool_call_limit"
    RUNTIME_LIMIT = "runtime_limit"
    REPEATED_BEHAVIOR = "repeated_behavior"
    SAFETY_TRIGGER = "safety_trigger"
    INVALID_TOOL_ARGUMENTS = "invalid_tool_arguments"
    DISALLOWED_TOOL = "disallowed_tool"
    ERROR = "error"


class EventType(str, Enum):
    STARTED = "started"
    STEP_STARTED = "step_started"
    MODEL_RESPONSE = "model_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    GUARDRAIL_WARNING = "guardrail_warning"
    TERMINATED = "terminated"


class GuardrailEvent(BaseModel):
    code: str
    message: str
    step: int | None = None
    severity: str = "warning"


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict[str, Any]
    status: str
    output_preview: str = ""
    duration_ms: int = 0


class BudgetUsage(BaseModel):
    steps_used: int
    steps_limit: int
    tool_calls_used: int
    tool_calls_limit: int
    runtime_seconds: float
    runtime_limit_seconds: int
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0


class AgentEvent(BaseModel):
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step: int | None = None
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
