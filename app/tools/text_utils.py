from __future__ import annotations

import re
from collections import Counter
from typing import cast

from pydantic import BaseModel, Field

from app.tools.base import BaseTool


class TextUtilsArgs(BaseModel):
    operation: str = Field(..., pattern="^(summarize_text|extract_keywords|word_count)$")
    text: str = Field(..., min_length=1, max_length=12000)
    max_sentences: int = Field(default=2, ge=1, le=8)
    max_keywords: int = Field(default=8, ge=1, le=20)


class TextUtilsTool(BaseTool):
    name = "text_utils"
    description = "Basic text utilities: summarize_text, extract_keywords, and word_count."
    args_model = TextUtilsArgs

    async def execute(self, args: BaseModel) -> str:
        parsed = cast(TextUtilsArgs, args)

        if parsed.operation == "word_count":
            words = re.findall(r"\b\w+\b", parsed.text)
            return str(len(words))

        if parsed.operation == "summarize_text":
            sentences = re.split(r"(?<=[.!?])\s+", parsed.text.strip())
            summary = " ".join(sentences[: parsed.max_sentences]).strip()
            return summary or parsed.text[:200]

        words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", parsed.text)]
        stop = {"this", "that", "with", "from", "have", "will", "would", "should", "about"}
        counts = Counter(w for w in words if w not in stop)
        keywords = [item for item, _ in counts.most_common(parsed.max_keywords)]
        return ", ".join(keywords)
