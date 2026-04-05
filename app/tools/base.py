from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolExecutionError(Exception):
    pass


class ToolValidationError(ToolExecutionError):
    pass


class BaseTool(ABC):
    name: str
    description: str
    args_model: type[BaseModel]

    @property
    def json_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    def validate_args(self, payload: dict[str, Any]) -> BaseModel:
        try:
            return self.args_model.model_validate(payload)
        except Exception as exc:
            raise ToolValidationError(str(exc)) from exc

    @abstractmethod
    async def execute(self, args: BaseModel) -> str:
        raise NotImplementedError
