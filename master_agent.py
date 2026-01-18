from typing import Any, Dict, Optional, List
from agents import Agent, Runner, function_tool
import json

class MasterAgent:
    """
    Master agent responsible for planning and delegating tasks to subagents.
    """
    def __init__(self, mcp_tools_descriptions: str, mcp_agent: Any):
        self.mcp_tools_descriptions = mcp_tools_descriptions
        self.mcp_agent = mcp_agent
        
        # Define task_tool for delegating to MCP agent
        @function_tool(
            name_override="task_tool",
            description_override="Delegates a specific task to the MCP worker agent.",
            strict_mode=False
        )
        async def task_tool(task: str, context: Dict[str, Any] = None) -> str:
            """
            Delegate a task to the MCP worker agent.
            
            Args:
                task: Detailed description of the task to perform
                context: Optional context data needed for the task
            
            Returns:
                The result from the MCP worker agent
            """
            if context is None:
                context = {}
            
            print(f"TaskTool invoked to switch to subagent. '{task}'")
            result = await self.mcp_agent.execute_task(task, context)
            
            if result.is_error:
                return f"McpAgent Error: {result.output}"
            return result.output
        
        self.agent = Agent(
            name="MasterAgent",
            instructions=f"""
            You are an intelligent master agent overseeing a patent analysis system.
            You are responsible for analyzing the user's request and coordinating with a worker agent.
            
            WORKER CAPABILITIES:
            {self.mcp_tools_descriptions.strip()}
            
            GUIDELINES:
            - Use the task_tool to delegate specific tasks to the worker agent when needed
            - When you have a complete answer to the user's request, provide it directly in your response
            - Be concise but thorough in your responses
            - Synthesize information from multiple tool calls if necessary
            """,
            model="gpt-4o",
            tools=[task_tool]
        )

    async def run(self, input_text: str, session: Any = None) -> str:
        """
        Executes the master agent for a single turn.
        """
        result = await Runner.run(self.agent, input_text, session=session)
        return result.final_output
