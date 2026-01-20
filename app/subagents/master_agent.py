import json
from typing import Any, Dict, Optional, List
from agents import Agent, Runner, function_tool
from app.config import config
from app.logger import logger
from app.prompt.master import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tools import Terminate, ToolCollection
from app.subagents.react_toolcall import ToolCallAgent
from app.subagents.mcp import MCPAgent
from app.subagents.capability import AgentCapability
from app.tools.subagent_task import SubAgentTaskTool


class MasterAgent(ToolCallAgent):
    """
    Master agent responsible for planning and delegating tasks to subagents.
    """
    name: str = "MasterAgent"
    description: str = "A patent analysis agent that can solve various tasks using multiple tools including MCP-based tools"

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 2
    _initialized: bool = False  # async wait for dependencies to be initialized

    @classmethod
    async def create(cls, **kwargs) -> "MasterAgent":
        """
        Factory method to create and fully initialize the MasterAgent
        with subagents and delegation tools.
        """
        instance = cls(**kwargs)

        # create subagents, async wait for it to connect to the server.
        mcp_agent = MCPAgent()
        await mcp_agent.initialize(
            connection_type="sse",
            server_url="http://0.0.0.0:8000/sse",
        )

        instance.subagents = {
            "McpAgent": mcp_agent,
        }

        # create delegation tool.
        subagent_task_tool = SubAgentTaskTool(
            subagents=instance.subagents
        )

        # MasterAgent does not know MCP tools, only knows delegation tool
        instance.available_tools.add_tool(subagent_task_tool)

        instance._initialized = True
        return instance

    def describe(self) -> AgentCapability:
        return AgentCapability(
            name=self.name,
            description=self.description,
            capabilities=[
                "solve patent related tasks in steps using subagents and tools",
            ],
            affordances=[
                "Patent analysis and FTO check.",
            ],
            limitations=[
                "Only Patent related tasks so far",
            ],
        )

    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        if not self._initialized:
            return False

        original_prompt = self.next_step_prompt
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        
        result = await super().think()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result
