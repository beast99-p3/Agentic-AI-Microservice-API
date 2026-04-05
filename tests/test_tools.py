from app.tools.registry import ToolRegistry
from app.tools.safe_math import SafeMathTool
from app.tools.text_utils import TextUtilsTool
from app.tools.web_fetch_stub import WebFetchStubTool


def test_tool_registry_lists_tools() -> None:
    registry = ToolRegistry([SafeMathTool(), TextUtilsTool(), WebFetchStubTool()])
    names = registry.list_tool_names()
    assert "safe_math" in names
    assert "text_utils" in names
    assert "web_fetch_stub" in names
