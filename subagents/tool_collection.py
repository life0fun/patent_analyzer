from typing import Any, Dict, List, Optional
from .mcp_client import MCPClient

class ToolResult:
    def __init__(self, output: str, is_error: bool = False):
        self.output = output
        self.is_error = is_error

    def __str__(self):
        return self.output

class ToolFailure(ToolResult):
    def __init__(self, error: str):
        super().__init__(output=error, is_error=True)

class MCPToolsCollection:
    """
    Encapsulates a collection of MCP tools.
    """
    def __init__(self, tools: List[Any]):
        self._tool_map = {tool.name: tool for tool in tools}

    def get_tool(self, name: str) -> Optional[Any]:
        return self._tool_map.get(name)

    def __iter__(self):
        return iter(self._tool_map.values())
