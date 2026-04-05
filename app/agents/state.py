from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from app.schemas.events import AgentEvent, BudgetUsage, GuardrailEvent, TerminationReason, ToolCallRecord


@dataclass(slots=True)
class RuntimeState:
    request_id: str
    task: str
    steps_used: int = 0
    tool_calls_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    warnings: list[GuardrailEvent] = field(default_factory=lambda: cast(list[GuardrailEvent], []))
    trace: list[AgentEvent] = field(default_factory=lambda: cast(list[AgentEvent], []))
    tool_calls: list[ToolCallRecord] = field(default_factory=lambda: cast(list[ToolCallRecord], []))
    final_answer: str = ""
    termination_reason: TerminationReason = TerminationReason.ERROR


@dataclass(slots=True)
class RuntimeResult:
    request_id: str
    final_answer: str
    termination_reason: TerminationReason
    warnings: list[GuardrailEvent]
    step_trace: list[AgentEvent]
    tool_calls: list[ToolCallRecord]
    budget_usage: BudgetUsage
    metadata: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))
