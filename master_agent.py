from typing import Any, Dict, Optional, List
from agents import Agent, Runner
import json

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
