from fastapi import APIRouter, Depends

from app.api.deps import get_tool_registry
from app.schemas.responses import ToolDescriptor, ToolsResponse
from app.tools.registry import ToolRegistry

router = APIRouter(tags=["tools"])


@router.get("/tools", response_model=ToolsResponse)
async def list_tools(registry: ToolRegistry = Depends(get_tool_registry)) -> ToolsResponse:
    tools = [
        ToolDescriptor(name=tool.name, description=tool.description, args_schema=tool.json_schema)
        for tool in registry.list_tools()
    ]
    return ToolsResponse(tools=tools)
