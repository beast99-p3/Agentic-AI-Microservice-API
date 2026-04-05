from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_prompt_preview_behavior() -> None:
    response = client.post(
        "/prompt/preview",
        json={
            "task": "Design a migration plan",
            "max_steps": 5,
            "max_tool_calls": 7,
            "max_runtime_seconds": 40,
            "allowed_tools": ["safe_math"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "composed_system_prompt" in body
    assert body["runtime_settings"]["max_steps"] == 5
    assert body["available_tools"] == ["safe_math"]
