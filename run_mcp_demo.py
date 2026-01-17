import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from agent import PatentAgent

# Claim A: A drone with specific features
CLAIM_A = """
1. A method for controlling an unmanned aerial vehicle (UAV), comprising:
receiving a first signal from a remote controller;
identifying a target location based on the first signal;
calculating a flight path to the target location; and
actuating a motor to propel the UAV along the flight path.
"""

# Claim B: Similar but with added obstacle avoidance
CLAIM_B = """
1. A method for operating a drone, comprising:
receiving a command signal from a user device;
determining a destination based on the command signal;
detecting an obstacle in a projected path;
computing an alternative route to the destination; and
controlling a propulsion system to move the drone along the alternative route.
"""

async def run():
    # Configure the server parameters
    server_params = StdioServerParameters(
        command=sys.executable, # Use the current python interpreter
        args=["-m", "patent_agent.mcp_server"], # Run the module
        env=None 
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Connected to server. Found {len(tools.tools)} tools.")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            # Call the tool
            print("\nCalling 'compare_claims'...")
            result = await session.call_tool(
                "compare_claims",
                arguments={"claim_a": CLAIM_A, "claim_b": CLAIM_B}
            )

            # Print result
            # The result content is a list of TextContent or ImageContent
            print("\nResult:")
            for content in result.content:
                if content.type == "text":
                    print(content.text)

if __name__ == "__main__":
    asyncio.run(run())
