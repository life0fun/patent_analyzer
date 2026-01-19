from typing import List
from pydantic import BaseModel, Field


class AgentCapability(BaseModel):
    """
    Machine- and LLM-readable description of an agent's abilities.
    """

    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="High-level purpose of the agent")

    capabilities: List[str] = Field(
        ..., description="Concrete abilities the agent has"
    )
    affordances: List[str] = Field(
        ..., description="Types of tasks the agent is best suited for"
    )
    limitations: List[str] = Field(
        ..., description="Known limitations or unsupported tasks"
    )
