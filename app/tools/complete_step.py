"""
app/tools/complete_step.py

A tool MasterAgent calls to signal to PlanningFlow that it has finished a step.
This replaces the misuse of `terminate` as a step-completion signal.

Design rationale
----------------
Previously MasterAgent had two options:
  1. return normally  → PlanningFlow marks complete blindly (no validation)
  2. call terminate   → entire flow stops

Neither allowed MasterAgent to say "this step succeeded/failed, here's why".
CompleteStepTool adds that missing signal without stopping the flow.

Usage by MasterAgent
--------------------
When MasterAgent finishes work for a step it calls:

    complete_step(
        status="success",
        output="Extracted 5 features: UAV control, signal reception, ...",
    )

or on failure:

    complete_step(
        status="failed",
        error="MCP server unavailable: ClaimAnalyzer has no attribute 'parser'",
        should_retry=True,
    )

PlanningFlow reads the serialized StepResult from the tool's return value and
makes an informed decision about what to do next.
"""

import json
from typing import ClassVar, Optional, Any

from pydantic import Field

from app.schema import StepResult, StepStatus
from app.tools.base import BaseTool, ToolResult


_COMPLETE_STEP_DESCRIPTION = """
Signal that the current plan step is finished and report the outcome.
Call this tool when you have completed all work for the current step.
Do NOT call terminate — use this tool instead.

Parameters
----------
status : "success" | "failed" | "partial" | "skipped"
    success  - step completed, output is valid
    failed   - step could not be completed (tool error, unavailable service, etc.)
    partial  - some work was done but not fully complete
    skipped  - step was not applicable (e.g. already done in a previous step)

output : str
    Human-readable summary of what was accomplished.
    Required when status is "success" or "partial".

error : str (optional)
    Description of the problem. Required when status is "failed" or "partial".

should_retry : bool (optional, default false)
    Set to true if the failure is transient and the planner should retry this step.
""".strip()


class CompleteStepTool(BaseTool):
    """
    MasterAgent calls this to report step outcome to PlanningFlow.
    The serialized StepResult is embedded in the tool's return string so that
    PlanningFlow._execute_step() can deserialize and act on it.
    """

    name: str = "complete_step"
    description: str = _COMPLETE_STEP_DESCRIPTION
    # agent reference injected so it can set state
    _agent: Optional[Any] = None

    # Marker prefix so PlanningFlow can reliably detect a StepResult payload
    # even if the LLM adds surrounding text.
    RESULT_PREFIX: ClassVar[str] = "STEP_RESULT:"

    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["success", "failed", "partial", "skipped"],
                "description": "Outcome of the step",
            },
            "output": {
                "type": "string",
                "description": "Summary of what was accomplished",
            },
            "error": {
                "type": "string",
                "description": "Error detail if status is failed or partial",
            },
            "should_retry": {
                "type": "boolean",
                "description": "Whether the planner should retry this step",
                "default": False,
            },
        },
        "required": ["status"],
    }

    async def execute(
        self,
        status: str,
        output: str = "",
        error: Optional[str] = None,
        should_retry: bool = False,
        **kwargs,
    ) -> ToolResult:
        try:
            step_status = StepStatus(status)
        except ValueError:
            step_status = StepStatus.FAILED
            error = f"Invalid status value '{status}' provided to complete_step"
        # wrap tool call argument(output) as the tool result.
        result = StepResult( 
            status=step_status,
            output=output,
            error=error,
            should_retry=should_retry,
        )
        # Signal the run() loop to stop — same mechanism as Terminate
        if self._agent:
            self._agent.state = AgentState.FINISHED
        
        # Embed serialized result with a known prefix so PlanningFlow can parse it
        payload = f"{self.RESULT_PREFIX}{result.model_dump_json()}"
        return ToolResult(output=payload)

    @staticmethod
    def parse_from_tool_output(raw: str) -> Optional[StepResult]:
        """
        PlanningFlow calls this to extract a StepResult from the raw string
        returned by _execute_step().  Returns None if no StepResult is embedded.
        """
        prefix = CompleteStepTool.RESULT_PREFIX
        idx = raw.find(prefix)
        if idx == -1:
            return None
        try:
            json_str = raw[idx + len(prefix):]
            # Take only the first JSON object (there may be trailing text)
            data = json.loads(json_str.split("\n")[0].strip())
            return StepResult(**data)
        except Exception:
            return None
