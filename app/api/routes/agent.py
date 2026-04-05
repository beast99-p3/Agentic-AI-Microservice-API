from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.runtime import AgentRuntime
from app.api.deps import get_runtime
from app.core.config import get_settings
from app.schemas.events import AgentEvent
from app.schemas.requests import AgentRunRequest, AgentStreamRequest
from app.schemas.responses import AgentRunResponse

router = APIRouter(tags=["agent"])


@router.post("/agent/run", response_model=AgentRunResponse)
async def run_agent(
    payload: AgentRunRequest,
    runtime: AgentRuntime = Depends(get_runtime),
) -> AgentRunResponse:
    try:
        result = await runtime.run(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent runtime error: {exc}") from exc

    return AgentRunResponse(
        request_id=result.request_id,
        final_answer=result.final_answer,
        termination_reason=result.termination_reason,
        warnings=result.warnings,
        tool_calls=result.tool_calls,
        step_trace=result.step_trace,
        budget_usage=result.budget_usage,
    )


@router.post("/agent/stream")
async def stream_agent(
    payload: AgentStreamRequest,
    runtime: AgentRuntime = Depends(get_runtime),
) -> StreamingResponse:
    settings = get_settings()
    if not settings.enable_stream_endpoint:
        raise HTTPException(status_code=503, detail="Streaming endpoint is disabled by configuration")

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def on_event(event: AgentEvent) -> None:
        await queue.put({"type": "event", "payload": event.model_dump(mode="json")})

    async def runner() -> None:
        try:
            result = await runtime.run(payload, event_handler=on_event)
            await queue.put(
                {
                    "type": "result",
                    "payload": {
                        "request_id": result.request_id,
                        "final_answer": result.final_answer,
                        "termination_reason": result.termination_reason.value,
                        "warnings": [item.model_dump(mode="json") for item in result.warnings],
                        "budget_usage": result.budget_usage.model_dump(mode="json"),
                    },
                }
            )
        except Exception as exc:
            await queue.put({"type": "error", "payload": {"detail": str(exc)}})
        finally:
            await queue.put({"type": "done", "payload": {}})

    async def event_generator() -> AsyncIterator[str]:
        task = asyncio.create_task(runner())
        try:
            while True:
                item = await queue.get()
                yield f"data: {json.dumps(item)}\n\n"
                if item["type"] == "done":
                    break
        finally:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")
