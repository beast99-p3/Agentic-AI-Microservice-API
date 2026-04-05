from __future__ import annotations

import asyncio
import json
import time
from typing import Any, cast

from app.core.security import sanitize_tool_output
from app.tools.base import BaseTool, ToolExecutionError, ToolValidationError


class ToolRegistry:
    def __init__(self, tools: list[BaseTool]):
        self._tools = {tool.name: tool for tool in tools}

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def list_tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def function_specs(self, allowlist: set[str] | None = None) -> list[dict[str, Any]]:
        tools = self._filtered_tools(allowlist)
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.json_schema,
            }
            for tool in tools
        ]

    async def execute(
        self,
        tool_name: str,
        raw_arguments: str,
        timeout_seconds: int,
        allowlist: set[str] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        tool = self.get(tool_name)
        if tool is None:
            raise ToolExecutionError(f"Unknown tool: {tool_name}")

        if allowlist and tool_name not in allowlist:
            raise ToolExecutionError(f"Tool '{tool_name}' is not in the current allowlist")

        try:
            raw: Any = json.loads(raw_arguments) if raw_arguments else {}
            if not isinstance(raw, dict):
                raise ToolValidationError("Tool arguments must be a JSON object")
            arguments = cast(dict[str, Any], raw)
        except json.JSONDecodeError as exc:
            raise ToolValidationError(f"Invalid JSON arguments: {exc}") from exc

        validated = tool.validate_args(arguments)
        started = time.perf_counter()
        raw_output = await asyncio.wait_for(tool.execute(validated), timeout=timeout_seconds)
        duration_ms = int((time.perf_counter() - started) * 1000)

        normalized = sanitize_tool_output(raw_output)
        meta: dict[str, Any] = {
            "tool": tool_name,
            "duration_ms": duration_ms,
            "args": arguments,
        }
        return normalized, meta

    def _filtered_tools(self, allowlist: set[str] | None) -> list[BaseTool]:
        if not allowlist:
            return self.list_tools()
        return [tool for tool in self.list_tools() if tool.name in allowlist]
