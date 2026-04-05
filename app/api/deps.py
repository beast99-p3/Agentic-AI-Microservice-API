from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from app.agents.runtime import AgentRuntime
from app.core.config import Settings, get_settings
from app.llm.openai_compatible import OpenAICompatibleClient
from app.tools.registry import ToolRegistry
from app.tools.safe_math import SafeMathTool
from app.tools.text_utils import TextUtilsTool
from app.tools.web_fetch_stub import WebFetchStubTool


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        tools=[
            SafeMathTool(),
            TextUtilsTool(),
            WebFetchStubTool(),
        ]
    )


@lru_cache
def get_llm_client() -> OpenAICompatibleClient:
    settings = get_settings()
    if not settings.llm_api_key:
        raise ValueError("Missing API key. Set GEMINI_API_KEY (or LLM_API_KEY) in .env.")

    return OpenAICompatibleClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )


def get_runtime(
    settings: Settings = Depends(get_settings),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
) -> AgentRuntime:
    client = get_llm_client()
    return AgentRuntime(settings=settings, llm_client=client, tool_registry=tool_registry)
