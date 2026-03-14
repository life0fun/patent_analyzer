from typing import Any, Dict

from app.tools import BaseTool
from pydantic import Field
from app.schema import AgentState
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

        # Run the subagent. Each tool call result is added to agent's memory as a
        # tool message. base.run() returns a formatted "Step N: ..." summary string
        # which buries the actual payload. We extract the real tool message content
        # from memory instead so MasterAgent receives the clean result.
        await agent.run(request=task)

        # Snapshot memory before resetting — we need to read results from it.
        messages_snapshot = list(agent.memory.messages)

        # Reset agent so it can be reused on the next plan-step delegation.
        # Without this, base.run() raises RuntimeError("Cannot run agent from state: FINISHED")
        # because terminate set agent.state = FINISHED.
        agent.state = AgentState.IDLE
        agent.current_step = 0
        agent.memory.clear()

        # Collect all tool-role messages (actual tool outputs) from the snapshot,
        # excluding terminate calls which carry no useful payload.
        tool_results = [
            msg.content
            for msg in messages_snapshot
            if msg.role == "tool"
            and msg.content
            and "terminate" not in (msg.name or "").lower()
        ]

        if tool_results:
            # Return the last meaningful tool result (the analysis output)
            return tool_results[-1]

        # Fallback: no tool messages found, return the last assistant message
        assistant_results = [
            msg.content
            for msg in messages_snapshot
            if msg.role == "assistant" and msg.content
        ]
        return assistant_results[-1] if assistant_results else "No result returned by subagent."
