import asyncio
import time

import sys
print(sys.path)

from app.subagents.master_agent import MasterAgent
from app.config import config
from app.flow.flow_factory import FlowFactory, FlowType
from app.logger import logger

REPORT_PATH = "report.txt"

def _write_report(content: str, flow=None) -> None:
    report_content = content
    if flow and flow.step_outputs:
        report_content += "\n\n" + "=" * 40 + "\n"
        report_content += "DETAILED STEP RESULTS\n"
        report_content += "=" * 40 + "\n\n"
        for i, out in sorted(flow.step_outputs.items()):
            report_content += f"### Step {i} Output\n{out}\n\n"
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Report written to {REPORT_PATH}")


async def run_flow():
    agents = {
        "master_agent": await MasterAgent.create(),
    }
    if config.run_flow_config.use_data_analysis_agent:
        agents["data_analysis"] = DataAnalysis()

    flow = None  # keep reference accessible in except handlers
    try:
        prompt = input("Enter your prompt: ")

        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        logger.warning("Processing your request...")

        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                flow.execute(prompt),
                timeout=3600,  # 60 minute timeout for the entire execution
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
            _write_report(result, flow=flow)
        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            logger.info(
                "Operation terminated due to timeout. Please try a simpler request."
            )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
    except asyncio.CancelledError:
        # anyio cancel-scope interop: the plan steps finished but the final
        # LLM summary call was cancelled.  Write whatever step outputs we have.
        logger.warning(
            "Flow cancelled during teardown (anyio/asyncio cancel scope interop)."
        )
        if flow is not None:
            _write_report("Plan execution summary was cancelled during teardown.", flow=flow)
        else:
            logger.warning("No flow object available to write report.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        # Centralized cleanup: close all SSE sessions and connections once at the end.
        logger.info("🎬 Starting final teardown...")
        try:
            if flow is not None:
                await flow.cleanup()
            for name, agent in agents.items():
                if hasattr(agent, "cleanup"):
                    await agent.cleanup()
        except Exception as cleanup_err:
            logger.debug(f"Teardown had issues (often anyio interop): {cleanup_err}")
        logger.info("✨ Flow terminated.")


if __name__ == "__main__":
    asyncio.run(run_flow())