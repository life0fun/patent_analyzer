import json
from typing import Any, Dict, Optional, List
from pydantic import Field, model_validator
from app.config import config
from app.logger import logger
from app.prompt.master import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tools import Terminate, ToolCollection, StrReplaceEditor, CompleteStepTool
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

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.root_path)
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            StrReplaceEditor(),
            CompleteStepTool(),   # replaces Terminate — reports step outcome  
            Terminate(),
        )
    )

    max_observe: int = 10000
    max_steps: int = 5  # This is agent loop steps, not plan steps. At least 2 needed: step 1 = subagent_task, step 2 = complete_step. Step 3 allows one recovery step.
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
        # Give McpAgent file-reading and terminate tools.
        # MCPClients inherits from ToolCollection, so add_tool() works directly.
        mcp_agent.mcp_clients.add_tool(StrReplaceEditor())
        mcp_agent.mcp_clients.add_tool(Terminate())

        instance.subagents = {
            "McpAgent": mcp_agent,
        }

        # create delegation tool.
        subagent_task_tool = SubAgentTaskTool(
            subagents=instance.subagents
        )

        # MasterAgent does not know MCP tools, only knows delegation tool
        instance.available_tools.add_tool(subagent_task_tool)
        complete_step_tool = CompleteStepTool()
        complete_step_tool._agent = instance        # ← inject here, once
        instance.available_tools.add_tool(complete_step_tool)

        instance._initialized = True
        logger.info(f" ** MasterAgent created with available tools {instance.available_tools.to_params()}")
        return instance

    def describe(self) -> AgentCapability:
        return AgentCapability(
            name=self.name,
            description=self.description,
            capabilities=[
                "solve patent related tasks in steps using subagents and tools",
            ],
            affordances=[
                "Patent claim analysis and Doctrine of Equivent check using function-way-result analysis.",
            ],
            limitations=[
                "Only Patent related tasks so far",
            ],
        )

    def reset_for_new_step(self) -> None:
        """
        Called by PlanningFlow._execute_step() before executor.run().
        Clear per-step memory so the LLM starts fresh for each plan step.

        Without this, the LLM sees its entire history and tends to say
        "I already did this in a previous step" instead of executing the task.
        The system_prompt (which includes global context) is preserved because
        it is injected separately by think() via system_msgs, not stored in memory.
        """
        self.memory.clear()
        logger.debug(f"🔄 {self.name} memory reset for new step")

    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        if not self._initialized:
            return False

        # defensive save next_step_prompt to avoid downstream modification.
        original_prompt = self.next_step_prompt
        
        result = await super().think()

        # Restore original next_step_prompt so it can be injected next think.
        self.next_step_prompt = original_prompt

        return result

    async def cleanup(self) -> None:
        """Clean up all subagents and resources."""
        logger.info(f"🧹 MasterAgent cleaning up {len(self.subagents)} subagents...")
        for name, agent in self.subagents.items():
            try:
                await agent.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up subagent {name}: {e}")
        await super().cleanup()
