from typing import Any, Dict, Optional, List
from agents import Agent, Runner, function_tool
import json
from .tool_collection import MCPToolsCollection, ToolResult
from .mcp_client import MCPClient
from .mcp_tool_adapter import adapt_mcp_tool

class McpAgent:
    """
    Subagent that wraps the MCP client and handles tool execution via semantic matching.
    """
    @classmethod
    async def create(cls, mcp_client: MCPClient):
        """
        Async factory method to create and initialize McpAgent.
        """
        mcp_tools = await mcp_client.list_tools()
        return cls(mcp_client, mcp_tools)

    def __init__(self, mcp_client: MCPClient, mcp_tools: List[Any]):
        self.mcp_client = mcp_client
        self.mcp_tools_collection = MCPToolsCollection(mcp_tools)
        
        # Initialize the internal Agent immediately
        converted_tools = []
        
        for tool in mcp_tools:
            # Assuming tool.inputSchema is the dict we need
            # If tool.inputSchema is a string, we might need to parse it, but usually it's a dict in MCP SDK
            adapted = adapt_mcp_tool(
                mcp_tool_name=tool.name,
                mcp_tool_description=tool.description,
                mcp_tool_schema=tool.inputSchema,
                executor=self.mcp_client.execute # Use client execute loop directly
            )
            converted_tools.append(adapted)
            
        self.agent = Agent(
            name="McpAgent",
            instructions="You are a patent analysis assistant. You have access to tools to compare claims, extract features, etc. Use them to answer the user's request. Always output the result of the tool call.",
            model="gpt-4o",
            tools=converted_tools
        )
        print(f"McpAgent initialized with {len(converted_tools)} tools.")

    async def execute_task(self, task_description: str, context: Dict[str, str]) -> ToolResult:
        """
        Executes the task using the native tool-enabled Agent.
        """
        print(f"McpAgent: execute_task: '{task_description}'")
        
        prompt = f"""
        Task: {task_description}
        
        Context:
        {json.dumps(context, indent=2)}
        """
        
        # Runner.run should handle tool calls automatically if tools are configured
        result = await Runner.run(self.agent, prompt)
        
        # return the final output
        return ToolResult(output=result.final_output)

    async def get_tools_descriptions(self) -> str:
        """
        Returns a brief description of the subagent's capabilities.
        """
        try:
            capabilities = "The Patent Subagent can perform the following tasks:\n"
            for tool in self.mcp_tools_collection:
                capabilities += f"- {tool.name}: {tool.description}\n"
            return capabilities
        except Exception as e:
            return f"Error fetching capabilities: {e}"
