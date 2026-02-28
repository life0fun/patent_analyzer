from app.tools.complete_step import CompleteStepTool
import json
import time
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import Field

from app.subagents.base import BaseAgent
from app.flow.base import BaseFlow
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message, ToolChoice
from app.tools.planning import PlanningTool
from app.prompt.planning import SYSTEM_PROMPT
from app.schema import StepResult, StepStatus

class PlanStepStatus(str, Enum):
    """Enum class defining possible statuses of a plan step"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

    @classmethod
    def get_all_statuses(cls) -> list[str]:
        """Return a list of all possible step status values"""
        return [status.value for status in cls]

    @classmethod
    def get_active_statuses(cls) -> list[str]:
        """Return a list of values representing active statuses (not started or in progress)"""
        return [cls.NOT_STARTED.value, cls.IN_PROGRESS.value]

    @classmethod
    def get_status_marks(cls) -> Dict[str, str]:
        """Return a mapping of statuses to their marker symbols"""
        return {
            cls.COMPLETED.value: "[✓]",
            cls.IN_PROGRESS.value: "[→]",
            cls.BLOCKED.value: "[!]",
            cls.NOT_STARTED.value: "[ ]",
        }


class PlanningFlow(BaseFlow):
    """A flow that manages planning and execution of tasks using agents."""

    llm: LLM = Field(default_factory=lambda: LLM())
    planning_tool: PlanningTool = Field(default_factory=PlanningTool)
    executor_keys: List[str] = Field(default_factory=list)
    active_plan_id: str = Field(default_factory=lambda: f"plan_{int(time.time())}")
    current_step_index: Optional[int] = None

    # How many times a step can be retried before being marked BLOCKED
    max_step_retries: int = Field(default=1)
    _step_retry_counts: Dict[int, int] = {}

    def __init__(
        self,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **data,
    ):
        if "executors" in data:
            data["executor_keys"] = data.pop("executors")
        if "plan_id" in data:
            data["active_plan_id"] = data.pop("plan_id")
        if "planning_tool" not in data:
            data["planning_tool"] = PlanningTool()

        super().__init__(agents, **data)

        if not self.executor_keys:
            self.executor_keys = list(self.agents.keys())

        self._step_retry_counts = {}

    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        if step_type and step_type in self.agents:
            return self.agents[step_type]
        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]
        return self.primary_agent


    async def execute(self, input_text: str) -> str:
        try:
            if not self.primary_agent:
                raise ValueError("No primary agent available")

            if input_text:
                await self._create_initial_plan(input_text)
                if self.active_plan_id not in self.planning_tool.plans:
                    logger.error(f"Plan creation failed for ID {self.active_plan_id}")
                    return f"Failed to create plan for: {input_text}"

            result = ""
            while True:
                self.current_step_index, step_info = await self._get_current_step_info()

                if self.current_step_index is None:
                    result += await self._finalize_plan()
                    break

                step_type = step_info.get("type") if step_info else None
                executor = self.get_executor(step_type)

                step_result = await self._execute_step(executor, step_info)
                result += step_result + "\n"

                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    logger.warning(
                        "Executor reached FINISHED state — stopping flow early. "
                        "MasterAgent should use complete_step, not terminate."
                    )
                    break

            return result

        except Exception as e:
            logger.error(f"Error in PlanningFlow: {e}")
            return f"Execution failed: {e}"

    async def _create_initial_plan(self, request: str) -> None:
        """Create an initial plan based on the request using the flow's LLM and PlanningTool."""
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        # system_message_content = (
        #     "You are a planning assistant. Create a concise, actionable plan with clear steps. "
        #     "Focus on key milestones rather than detailed sub-steps. "
        #     "Optimize for clarity and efficiency."
        # )
        system_message_content = SYSTEM_PROMPT
        agents_description = []
        for key in self.executor_keys:
            if key in self.agents:
                agents_description.append(
                    {
                        "name": key.upper(),
                        "description": self.agents[key].description,
                    }
                )
        if len(agents_description) > 1:
            # Add description of agents to select
            system_message_content += (
                f"\nNow we have {agents_description} agents. "
                f"The infomation of them are below: {json.dumps(agents_description)}\n"
                "When creating steps in the planning tool, please specify the agent names using the format '[agent_name]'."
            )

        # Create a system message for plan creation
        system_message = Message.system_message(system_message_content)

        # Create a user message with the request
        user_message = Message.user_message(
            f"Create a reasonable plan with clear steps to accomplish the task: {request}"
        )

        # Call LLM with PlanningTool
        response = await self.llm.ask_tool(
            messages=[user_message],
            system_msgs=[system_message],
            tools=[self.planning_tool.to_param()],
            tool_choice=ToolChoice.AUTO,
        )

        # Process tool calls if present
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "planning":
                    # Parse the arguments
                    args = tool_call.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse tool arguments: {args}")
                            continue

                    # Ensure plan_id is set correctly and execute the tool
                    args["plan_id"] = self.active_plan_id

                    # Execute the tool via ToolCollection instead of directly
                    result = await self.planning_tool.execute(**args)

                    logger.info(f"Plan creation result: {str(result)}")
                    return

        # If execution reached here, create a default plan
        logger.warning("Creating default plan")

        # Create default plan using the ToolCollection
        await self.planning_tool.execute(
            **{
                "command": "create",
                "plan_id": self.active_plan_id,
                "title": f"Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
                "steps": ["Analyze request", "Execute task", "Verify results"],
            }
        )

    async def _get_current_step_info(self) -> tuple[Optional[int], Optional[dict]]:
        """
        Parse the current plan to identify the first non-completed step's index and info.
        Returns (None, None) if no active step is found.
        """
        if (
            not self.active_plan_id
            or self.active_plan_id not in self.planning_tool.plans
        ):
            logger.error(f"Plan with ID {self.active_plan_id} not found")
            return None, None

        try:
            # Direct access to plan data from planning tool storage
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            # Find first non-completed step
            for i, step in enumerate(steps):
                if i >= len(step_statuses):
                    status = PlanStepStatus.NOT_STARTED.value
                else:
                    status = step_statuses[i]

                if status in PlanStepStatus.get_active_statuses():
                    # Extract step type/category if available
                    step_info = {"text": step}

                    # Try to extract step type from the text (e.g., [SEARCH] or [CODE])
                    import re

                    type_match = re.search(r"\[([A-Z_]+)\]", step)
                    if type_match:
                        step_info["type"] = type_match.group(1).lower()

                    # Mark current step as in_progress
                    try:
                        await self.planning_tool.execute(
                            command="mark_step",
                            plan_id=self.active_plan_id,
                            step_index=i,
                            step_status=PlanStepStatus.IN_PROGRESS.value,
                        )
                    except Exception as e:
                        logger.warning(f"Error marking step as in_progress: {e}")
                        # Update step status directly if needed
                        if i < len(step_statuses):
                            step_statuses[i] = PlanStepStatus.IN_PROGRESS.value
                        else:
                            while len(step_statuses) < i:
                                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
                            step_statuses.append(PlanStepStatus.IN_PROGRESS.value)

                        plan_data["step_statuses"] = step_statuses

                    return i, step_info

            return None, None  # No active step found

        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None, None

    def _build_step_prompt(self, step_info: dict) -> str:
        """
        Build the prompt handed to MasterAgent for a single step.
        Explicitly instructs MasterAgent to call complete_step when done.
        """
        step_text = step_info.get("text", "")
        step_index = step_info.get("index", "?")

        return (
            f"## Current Task (Plan Step {step_index})\n\n"
            f"{step_text}\n\n"
            f"## Instructions\n"
            f"Execute ONLY this step. Do not attempt other steps.\n"
            f"When you have finished (whether successfully or not), you MUST call "
            f"`complete_step` with:\n"
            f"  - status: 'success', 'failed', 'partial', or 'skipped'\n"
            f"  - output: summary of what you did\n"
            f"  - error: description of any problem (if status != success)\n"
            f"  - should_retry: true if the failure is likely transient\n"
            f"Do NOT call `terminate`."
        )

    async def _execute_step(self, executor: BaseAgent, step_info: dict) -> str:
        """
        Run MasterAgent on one plan step and handle the outcome.

        Flow:
            1. Mark step in_progress
            2. Reset agent memory (fresh context per step)
            3. Run executor — MasterAgent calls complete_step() at the end
            4. Parse StepResult from the raw output string
            5. Branch on status → mark completed / blocked / retry
        """
        step_index = self.current_step_index
        step_text  = step_info.get("text", f"Step {step_index}")

        # 1. Mark in_progress
        await self.planning_tool.execute(
            command="mark_step",
            plan_id=self.active_plan_id,
            step_index=step_index,
            step_status=PlanStepStatus.IN_PROGRESS,
        )

        # 2. Reset agent memory so LLM starts fresh for this step
        if hasattr(executor, "reset_for_new_step"):
            executor.reset_for_new_step()

        # 3. Build prompt and run
        step_prompt = self._build_step_prompt(step_info)
        logger.info(f"▶ Executing plan step {step_index}: {step_text}")
        raw_output = await executor.run(step_prompt)

        # 4. Parse StepResult
        step_result = CompleteStepTool.parse_from_tool_output(raw_output or "")

        # 5. Handle outcome
        return await self._handle_step_result(step_index, step_text, raw_output, step_result)

    async def _handle_step_result(
        self,
        step_index: int,
        step_text: str,
        raw_output: str,
        step_result: Optional[StepResult],
    ) -> str:
        """
        Decide what to do based on the StepResult returned by MasterAgent.
        """

        # ── No StepResult embedded (MasterAgent didn't call complete_step) ──
        if step_result is None:
            logger.warning(
                f"⚠ Step {step_index} did not return a StepResult "
                f"(MasterAgent may not have called complete_step). "
                f"Marking completed with caution."
            )
            await self._mark_step_completed(step_index)
            return raw_output or ""

        logger.info(
            f"Step {step_index} result: status={step_result.status.value} "
            + (f"| error={step_result.error}" if step_result.error else "")
        )

        # ── SUCCESS ──────────────────────────────────────────────────────────
        if step_result.status == StepStatus.SUCCESS:
            logger.info(f"✅ Step {step_index} completed successfully.")
            await self._mark_step_completed(step_index)
            return step_result.output

        # ── SKIPPED ──────────────────────────────────────────────────────────
        if step_result.status == StepStatus.SKIPPED:
            logger.info(f"⏭ Step {step_index} skipped: {step_result.output}")
            await self._mark_step_completed(step_index)
            return step_result.output

        # ── PARTIAL ──────────────────────────────────────────────────────────
        if step_result.status == StepStatus.PARTIAL:
            logger.warning(
                f"⚡ Step {step_index} partially completed. "
                f"Error: {step_result.error}. Marking completed and continuing."
            )
            await self._mark_step_completed(step_index)
            return step_result.output

        # ── FAILED ───────────────────────────────────────────────────────────
        if step_result.status == StepStatus.FAILED:
            retry_count = self._step_retry_counts.get(step_index, 0)

            if step_result.should_retry and retry_count < self.max_step_retries:
                # Reset to not_started so _get_current_step_info() picks it up again
                self._step_retry_counts[step_index] = retry_count + 1
                logger.warning(
                    f"🔄 Step {step_index} failed (retry {retry_count + 1}/"
                    f"{self.max_step_retries}): {step_result.error}"
                )
                await self.planning_tool.execute(
                    command="mark_step",
                    plan_id=self.active_plan_id,
                    step_index=step_index,
                    step_status=PlanStepStatus.NOT_STARTED,
                )
                return f"[retrying step {step_index}]"

            else:
                # Non-retryable failure or retries exhausted → mark BLOCKED
                logger.error(
                    f"❌ Step {step_index} failed and will be blocked. "
                    f"Error: {step_result.error}"
                )
                await self.planning_tool.execute(
                    command="mark_step",
                    plan_id=self.active_plan_id,
                    step_index=step_index,
                    step_status=PlanStepStatus.BLOCKED,
                )
                return f"[step {step_index} blocked: {step_result.error}]"

        # Fallback — unknown status
        await self._mark_step_completed(step_index)
        return raw_output or ""

    async def _mark_step_completed(self, step_index: Optional[int] = None) -> None:
        """Mark the given step (or the current step) as completed."""
        idx = step_index if step_index is not None else self.current_step_index
        if idx is None:
            return

        try:
            # Mark the step as completed
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=idx,
                step_status=PlanStepStatus.COMPLETED.value,
            )
            logger.info(
                f"Marked step {idx} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")
            # Update step status directly in planning tool storage
            if self.active_plan_id in self.planning_tool.plans:
                plan_data = self.planning_tool.plans[self.active_plan_id]
                step_statuses = plan_data.get("step_statuses", [])

                # Ensure the step_statuses list is long enough
                while len(step_statuses) <= idx:
                    step_statuses.append(PlanStepStatus.NOT_STARTED.value)

                # Update the status
                step_statuses[idx] = PlanStepStatus.COMPLETED.value
                plan_data["step_statuses"] = step_statuses

    async def _get_plan_text(self) -> str:
        """Get the current plan as formatted text."""
        try:
            result = await self.planning_tool.execute(
                command="get", plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            logger.error(f"Error getting plan: {e}")
            return self._generate_plan_text_from_storage()

    def _generate_plan_text_from_storage(self) -> str:
        """Generate plan text directly from storage if the planning tool fails."""
        try:
            if self.active_plan_id not in self.planning_tool.plans:
                return f"Error: Plan with ID {self.active_plan_id} not found"

            plan_data = self.planning_tool.plans[self.active_plan_id]
            title = plan_data.get("title", "Untitled Plan")
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])
            step_notes = plan_data.get("step_notes", [])

            # Ensure step_statuses and step_notes match the number of steps
            while len(step_statuses) < len(steps):
                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
            while len(step_notes) < len(steps):
                step_notes.append("")

            # Count steps by status
            status_counts = {status: 0 for status in PlanStepStatus.get_all_statuses()}

            for status in step_statuses:
                if status in status_counts:
                    status_counts[status] += 1

            completed = status_counts[PlanStepStatus.COMPLETED.value]
            total = len(steps)
            progress = (completed / total) * 100 if total > 0 else 0

            plan_text = f"Plan: {title} (ID: {self.active_plan_id})\n"
            plan_text += "=" * len(plan_text) + "\n\n"

            plan_text += (
                f"Progress: {completed}/{total} steps completed ({progress:.1f}%)\n"
            )
            plan_text += f"Status: {status_counts[PlanStepStatus.COMPLETED.value]} completed, {status_counts[PlanStepStatus.IN_PROGRESS.value]} in progress, "
            plan_text += f"{status_counts[PlanStepStatus.BLOCKED.value]} blocked, {status_counts[PlanStepStatus.NOT_STARTED.value]} not started\n\n"
            plan_text += "Steps:\n"

            status_marks = PlanStepStatus.get_status_marks()

            for i, (step, status, notes) in enumerate(
                zip(steps, step_statuses, step_notes)
            ):
                # Use status marks to indicate step status
                status_mark = status_marks.get(
                    status, status_marks[PlanStepStatus.NOT_STARTED.value]
                )

                plan_text += f"{i}. {status_mark} {step}\n"
                if notes:
                    plan_text += f"   Notes: {notes}\n"

            return plan_text
        except Exception as e:
            logger.error(f"Error generating plan text from storage: {e}")
            return f"Error: Unable to retrieve plan with ID {self.active_plan_id}"

    async def _finalize_plan(self) -> str:
        """Finalize the plan and provide a summary using the flow's LLM directly."""
        plan_text = await self._get_plan_text()

        # Create a summary using the flow's LLM directly
        try:
            system_message = Message.system_message(
                "You are a planning assistant. Your task is to summarize the completed plan."
            )

            user_message = Message.user_message(
                f"The plan has been completed. Here is the final plan status:\n\n{plan_text}\n\nPlease provide a summary of what was accomplished and any final thoughts."
            )

            response = await self.llm.ask(
                messages=[user_message], system_msgs=[system_message]
            )

            return f"Plan completed:\n\n{response}"
        except Exception as e:
            logger.error(f"Error finalizing plan with LLM: {e}")

            # Fallback to using an agent for the summary
            try:
                agent = self.primary_agent
                summary_prompt = f"""
                The plan has been completed. Here is the final plan status:

                {plan_text}

                Please provide a summary of what was accomplished and any final thoughts.
                """
                summary = await agent.run(summary_prompt)
                return f"Plan completed:\n\n{summary}"
            except Exception as e2:
                logger.error(f"Error finalizing plan with agent: {e2}")
                return "Plan completed. Error generating summary."