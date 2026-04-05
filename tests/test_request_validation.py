import pytest
from pydantic import ValidationError

from app.schemas.requests import AgentRunRequest


def test_request_validation_rejects_duplicate_allowed_tools() -> None:
    with pytest.raises(ValidationError):
        AgentRunRequest(
            task="Plan a migration",
            allowed_tools=["safe_math", "safe_math"],
        )


def test_request_validation_accepts_valid_payload() -> None:
    payload = AgentRunRequest(task="Analyze tradeoffs", max_steps=4, max_tool_calls=5)
    assert payload.max_steps == 4
    assert payload.max_tool_calls == 5
