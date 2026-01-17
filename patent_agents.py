from typing import Any, Dict, Optional, List
from tool_collection import MCPToolsCollection, ToolResult
from mcp_client import MCPClient
from agents import Agent, Runner, function_tool
import json

class McpAgent:
    """
    Subagent that wraps the MCP client and handles tool execution via semantic matching.
    """
    def __init__(self):
        self.mcp_client = MCPClient()
        self.mcp_tools_collection = MCPToolsCollection(self.mcp_client)
        self.agent = Agent(
            name="McpAgent",
            instructions="You are a tool selection specialist for a patent agent system. Based on the task and context, choose the BEST tool and provide the arguments.",
            model="gpt-4o"
        )

    async def list_tools(self):
        return await self.mcp_tools_collection.list_tools()

    async def get_tools_descriptions(self) -> str:
        """
        Returns a brief description of the subagent's capabilities (list of tool names or short descriptions).
        """
        try:
            tools = await self.list_tools()
            capabilities = "The Patent Subagent can perform the following tasks:\n"
            for tool in tools:
                capabilities += f"- {tool.name}\n"
            return capabilities
        except Exception as e:
            return f"Error fetching capabilities: {e}"

    async def execute_with_semantic_matching(self, task_description: str, context: Dict[str, str]) -> ToolResult:
        """
        Uses LLM to find the best tool for the task and executes it.
        """
        print(f"McpAgent: Analyzing task for semantic matching: '{task_description}'")
        
        try:
            tools = await self.list_tools()
            tools_info = ""
            for tool in tools:
                tools_info += f"- {tool.name}: {tool.description}. Input Schema: {tool.inputSchema}\n"
        except Exception as e:
            return ToolResult(output=f"Error fetching tools: {e}", is_error=True)

        prompt = f"""
        Task to perform: {task_description}
        
        Available Tools:
        {tools_info}
        
        Context Data (Variables you can use to fill arguments):
        {json.dumps(context, indent=2)}
        
        Return ONLY a JSON object: {{"tool": "tool_name", "arguments": {{...}}}}
        """
        
        result = await Runner.run(self.agent, prompt)
        decision_text = result.final_output
        
        # Handle potential markdown wrapping
        cleaned_text = decision_text.strip()
        if cleaned_text.startswith("```"):
            lines = cleaned_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_text = "\n".join(lines).strip()

        try:
            decision = json.loads(cleaned_text)
            tool_name = decision.get("tool")
            arguments = decision.get("arguments", {})
            
            if tool_name:
                print(f"McpAgent: Semantic matching selected tool `{tool_name}`. Executing...")
                return await self.mcp_tools_collection.execute(tool_name, arguments)
            else:
                return ToolResult(output="No tool selected by semantic matching.", is_error=True)
        except json.JSONDecodeError:
            return ToolResult(output=f"Failed to parse tool selection: {decision_text}", is_error=True)

class MasterAgent:
    """
    Master agent responsible for planning and delegating tasks to subagents.
    """
    def __init__(self, tools: List[Any], mcp_tools_descriptions: str):
        self.mcp_tools_descriptions = mcp_tools_descriptions
        
        self.agent = Agent(
            name="MasterAgent",
            instructions=f"""
            You are an intelligent master agent overseeing a patent analysis system.
            You can delegate patent-related tasks to the `mcp_agent` worker using the `task_tool`.
            The `mcp_agent` has these capabilities: {self.mcp_tools_descriptions.strip()}
            
            When you use `task_tool`, provide a detailed 'task' description and pass the relevant 'context'.
            """,
            model="gpt-4o",
            tools=tools
        )

    async def run(self, user_query: str, context: Dict[str, str]) -> str:
        """
        Executes the planning and delegation flow.
        """
        print("MasterAgent: Starting execution...")
        prompt = f"User Request: {user_query}\n\nContext:\n{json.dumps(context, indent=2)}"
        result = await Runner.run(self.agent, prompt)
        return result.final_output
