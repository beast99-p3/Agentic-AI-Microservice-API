from __future__ import annotations

import ast
from collections.abc import Callable
from typing import cast

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolExecutionError


class SafeMathArgs(BaseModel):
    expression: str = Field(..., min_length=1, max_length=200)


class SafeMathTool(BaseTool):
    name = "safe_math"
    description = "Evaluate a restricted arithmetic expression with +, -, *, /, %, and parentheses."
    args_model = SafeMathArgs

    _binary_ops: dict[type[ast.AST], Callable[[float, float], float]] = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.Mod: lambda a, b: a % b,
    }
    _unary_ops: dict[type[ast.AST], Callable[[float], float]] = {
        ast.USub: lambda a: -a,
        ast.UAdd: lambda a: +a,
    }

    async def execute(self, args: BaseModel) -> str:
        parsed = cast(SafeMathArgs, args)
        try:
            tree = ast.parse(parsed.expression, mode="eval")
            value = self._eval(tree.body)
            return str(value)
        except Exception as exc:
            raise ToolExecutionError(f"safe_math failed: {exc}") from exc

    def _eval(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)

        if isinstance(node, ast.BinOp) and type(node.op) in self._binary_ops:
            left = self._eval(node.left)
            right = self._eval(node.right)
            return self._binary_ops[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp) and type(node.op) in self._unary_ops:
            return self._unary_ops[type(node.op)](self._eval(node.operand))

        raise ToolExecutionError("Expression contains unsupported syntax")
