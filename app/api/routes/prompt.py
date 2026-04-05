from fastapi import APIRouter, Depends

from app.agents.prompts import compose_prompt_preview
from app.api.deps import get_tool_registry
from app.schemas.requests import PromptPreviewRequest
from app.schemas.responses import PromptPreviewResponse
from app.tools.registry import ToolRegistry

router = APIRouter(tags=["prompt"])


@router.post("/prompt/preview", response_model=PromptPreviewResponse)
async def preview_prompt(
    payload: PromptPreviewRequest,
    registry: ToolRegistry = Depends(get_tool_registry),
) -> PromptPreviewResponse:
    allowlist = payload.allowed_tools if payload.allowed_tools else registry.list_tool_names()
    preview = compose_prompt_preview(
        task=payload.task,
        system_prompt_override=payload.system_prompt_override,
        max_steps=payload.max_steps,
        max_tool_calls=payload.max_tool_calls,
        max_runtime_seconds=payload.max_runtime_seconds,
        available_tools=allowlist,
    )
    return PromptPreviewResponse(**preview)
