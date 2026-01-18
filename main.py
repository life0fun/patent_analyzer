import json
import asyncio
import argparse
from typing import Dict, Any
from agents import OpenAIConversationsSession
from master_agent import MasterAgent
from subagents.mcp_client import MCPClient
from subagents.mcp_agent import McpAgent

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
    
    # Initialize Agents
    mcp_client = MCPClient()
    mcp_agent = await McpAgent.create(mcp_client)
    mcp_tools_descriptions = await mcp_agent.get_tools_descriptions()

    # Create MasterAgent with task_tool registered
    master_agent = MasterAgent(
        mcp_tools_descriptions=mcp_tools_descriptions,
        mcp_agent=mcp_agent
    )
        
    context = {
        "claim_a": claim_a_text,
        "claim_b": claim_b_text
    }
    
    # Prepare input
    user_input = f"User Request: {user_query}\n\nContext:\n{json.dumps(context, indent=2)}"
    session = OpenAIConversationsSession()
    
    # Run the master agent - it handles the Think-Act-Observation loop internally
    print("\Main: Running MasterAgent (with internal Think-Act loop)...")
    result = await master_agent.run(user_input, session=session)
    
    # Display final result
    print("\n" + "="*40)
    print("FINAL RESULT:")
    print("="*40)
    print(result)
        
if __name__ == "__main__":
    asyncio.run(main())
