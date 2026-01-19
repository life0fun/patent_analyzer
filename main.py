import json
import asyncio
import argparse
from typing import Dict, Any
from agents import OpenAIConversationsSession
from app.logger import logger
from app.subagents.master_agent import MasterAgent


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
    
    context = {
        "claim_a": claim_a_text,
        "claim_b": claim_b_text
    }
    
    # Prepare input
    user_input = f"User Request: {user_query}\n\nContext:\n{json.dumps(context, indent=2)}"
    session = OpenAIConversationsSession()

    # Create MasterAgent with task_tool registered
    master_agent = await MasterAgent.create()

    try:
        logger.warning("Processing your request...")
        result = await master_agent.run(user_input)
        # Display final result
        print("\n" + "="*40)
        print("FINAL RESULT:")
        print("="*40)
        print(result)
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    finally:
        # Ensure agent resources are cleaned up before exiting
        await master_agent.cleanup()
    
if __name__ == "__main__":
    asyncio.run(main())
