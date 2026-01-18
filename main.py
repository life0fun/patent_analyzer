import asyncio
import argparse
from typing import Dict, Any
from master_agent import MasterAgent
from subagents.mcp_agent import McpAgent
from agents import function_tool

async def main():
    # Parse Command Line Arguments
    parser = argparse.ArgumentParser(description="Patent Agent Planner")
    parser.add_argument("claim_a_path", help="Path to text file containing Claim A")
    parser.add_argument("claim_b_path", help="Path to text file containing Claim B")
    args = parser.parse_args()

    try:
        with open(args.claim_a_path, "r") as f:
            claim_a_text = f.read().strip()
        with open(args.claim_b_path, "r") as f:
            claim_b_text = f.read().strip()
    except Exception as e:
        print(f"Error reading claim files: {e}")
        return

    user_query = "I want to check the similarity between these two patent claims to see if there is potential infringement."

    print(f"User Query: \"{user_query}\"")
    print("-" * 50)
    
    mcp_agent = McpAgent()
    mcp_tools_descriptions = await mcp_agent.get_tools_descriptions()

    @function_tool(name_override="task_tool", description_override="Delegates a specific task to the MCP worker agent.", strict_mode=False)
    async def task_tool(task: str, context: Dict[str, Any]):
        """
        Delegates a task to the mcp_agent.
        :param task: A detailed description of the patent analysis task to perform.
        :param context: Dictionary containing relevant data (e.g., 'claim_a', 'claim_b').
        """
        print(f"Orchestrator: Delegating task to McpAgent: '{task}'")
        result = await mcp_agent.execute_with_semantic_matching(task, context)
        if not result.is_error:
            return result.output
        else:
            return f"McpAgent Error: {result.output}"

    master_agent = MasterAgent(tools=[task_tool], mcp_tools_descriptions=mcp_tools_descriptions)
        
    context = {
        "claim_a": claim_a_text,
        "claim_b": claim_b_text
    }
    
    # 2. Execute
    print("Orchestrator: Requesting plan from MasterAgent...")
    final_answer = await master_agent.run(user_query, context)
    
    # 3. Final Output
    print("\n" + "="*40)
    print("FINAL ANSWER:")
    print("="*40)
    print(final_answer)

if __name__ == "__main__":
    asyncio.run(main())
