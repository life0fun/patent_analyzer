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
    Encapsulates a collection of MCP tools and provides a structured execution interface.
    """
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self._tool_map = {}

    async def list_tools(self) -> List[Any]:
        """
        Fetch and cache tools from the MCP server.
        """
        tools = await self.mcp_client.list_tools()
        self._tool_map = {tool.name: tool for tool in tools}
        return tools

    async def execute(
        self, name: str, tool_input: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Executes a tool by name with the provided input.
        """
        if not self._tool_map:
            # Auto-populate tool map if empty
            await self.list_tools()

        if name not in self._tool_map:
            return ToolFailure(error=f"Tool {name} is invalid")

        try:
            # Use the generic execute method of the mpc_client
            result_text = await self.mcp_client.execute(name, tool_input or {})
            return ToolResult(output=result_text)
        except Exception as e:
            return ToolFailure(error=f"Error executing tool {name}: {e}")
