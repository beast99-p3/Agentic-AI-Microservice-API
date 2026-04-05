from __future__ import annotations

from typing import cast

from pydantic import BaseModel, Field

from app.tools.base import BaseTool


class WebFetchStubArgs(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)


class WebFetchStubTool(BaseTool):
    name = "web_fetch_stub"
    description = "Restricted demo fetch tool. Returns canned content for a tiny allowlist only."
    args_model = WebFetchStubArgs

    _allowed_prefixes = (
        "https://example.com",
        "https://docs.python.org",
    )

    async def execute(self, args: BaseModel) -> str:
        parsed = cast(WebFetchStubArgs, args)

        if not any(parsed.url.startswith(prefix) for prefix in self._allowed_prefixes):
            return "Access denied by web_fetch_stub allowlist."

        return (
            "Stubbed fetch result:\n"
            f"url={parsed.url}\n"
            "content=This is synthetic demo content from a restricted fetch tool."
        )
