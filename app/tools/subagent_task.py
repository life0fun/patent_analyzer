from typing import Any, Dict

from app.tools import BaseTool
from pydantic import Field
from app.subagents.capability import AgentCapability
from app.subagents.base import BaseAgent

class SubAgentTaskTool(BaseTool):
    """
    Tool that allows a master agent to delegate a task to a self-describing subagent.
    """

    name: str = "subagent_task"
    description: str = (
        "Delegate a task to the most appropriate subagent based on its capabilities."
    )
    subagents: Dict[str, "BaseAgent"] = Field(default_factory=dict)
    agent_descriptions: Dict[str, AgentCapability] = Field(default_factory=dict)

    def __init__(self, subagents: Dict[str, "BaseAgent"]):
        super().__init__()
        self.subagents = subagents

        # Collect capability descriptions
        self.agent_descriptions = {
            name: agent.describe() for name, agent in subagents.items()
        }

        # Build LLM-facing description text
        agent_help_text = "\n\n".join(
            self._format_agent_description(desc)
            for desc in self.agent_descriptions.values()
        )

        # Build OpenAI tool schema
        self.parameters = {
            "type": "object",
            "properties": {
                "subagent": {
                    "type": "string",
                    "enum": list(subagents.keys()),
                    "description": (
                        "Choose the subagent best suited for the task.\n\n"
                        f"Available subagents:\n{agent_help_text}"
                    ),
                },
                "task": {
                    "type": "string",
                    "description": "The task to execute on the selected subagent.",
                },
            },
            "required": ["subagent", "task"],
            "additionalProperties": False,
        }

    def _format_agent_description(self, desc) -> str:
        return (
            f"- {desc.name}: {desc.description}\n"
            f"  Capabilities: {', '.join(desc.capabilities)}\n"
            f"  Best for: {', '.join(desc.affordances)}\n"
            f"  Limitations: {', '.join(desc.limitations)}"
        )

    async def execute(self, subagent: str, task: str, **kwargs) -> Any:
        agent = self.subagents.get(subagent)
        if agent is None:
            raise ValueError(f"Subagent '{subagent}' not found")

        # Delegate control to the agent. SubAgent can invoke multiple tool call steps, and each tool call result is added to agent's memory. 
        # When SubAgent think() decides to finish, it will call complete_step tool, pass the summarized result from all tool call steps and return the final result to master agent.
        return await agent.run(request=task)
