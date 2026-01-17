import os
import openai
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

@function_tool
def tool1():
    """Tool 1"""
    return "Result 1"

@function_tool
def tool2():
    """Tool 2"""
    return "Result 2"

import asyncio

async def test():
    agent = Agent(name="TestAgent", model="gpt-4o", tools=[tool1])
    print(f"Initial tools: {[t.name for t in agent.tools]}")

    agent.tools = [tool2]
    print(f"Updated tools: {[t.name for t in agent.tools]}")

    try:
        result = await Runner.run(agent, "Use tool2")
        print(f"Final Output: {result.final_output}")
        for item in result.new_items:
            if hasattr(item, 'call') and hasattr(item.call, 'function'):
                print(f"Tool Call: {item.call.function.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(test())
    else:
        print("Skipping test: No OpenAI key.")
