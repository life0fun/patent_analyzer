import asyncio
from typing import List
from contextlib import asynccontextmanager
from mcp.client.sse import sse_client
from mcp import ClientSession

class MCPClient:
    """
    A client that connects to the Patent Agent MCP server via SSE (HTTP).
    Default URL: http://localhost:8000/sse  
    """

    def __init__(self, url="http://localhost:8000/sse"):
        self.url = url

    @asynccontextmanager
    async def connect(self):
        """
        Async context manager to handle the connection lifecycle.
        """
        async with sse_client(self.url) as streams:
            # sse_client returns (read, write) streams, wrap in ClientSession
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                yield session

    async def list_tools(self):
        """
        List available tools from the MCP server.
        """
        async with self.connect() as session:
            # session.list_tools() returns a ListToolsResult or similar depending on implementation
            # In FastMCP/standard MCP it usually has a .tools attribute
            result = await session.list_tools()
            return result.tools if hasattr(result, "tools") else result

    async def execute(self, name: str, arguments: dict) -> str:
        """
        Generic method to call any tool by name with arguments.
        """
        async with self.connect() as session:
            result = await session.call_tool(
                name,
                arguments=arguments
            )
            return self._extract_text(result)

    async def compare_claims(self, claim_a: str, claim_b: str) -> str:
        """
        Convenience method to call the compare_claims tool.
        """
        return await self.execute("compare_claims", {"claim_a": claim_a, "claim_b": claim_b})

    async def extract_features(self, claim_text: str) -> str:
        """Call extract_features tool."""
        return await self.execute("extract_features", {"claim_text": claim_text})

    async def compare_features(self, features_a: List[str], features_b: List[str]) -> str:
        """Call compare_features tool."""
        return await self.execute(
            "compare_features",
            {
                "features_a": features_a,
                "features_b": features_b
            }
        )

    def _extract_text(self, result) -> str:
        output = []
        for content in result.content:
            if content.type == "text":
                output.append(content.text)
        return "\n".join(output)

# Example Usage Block
async def main():
    # If running in a true container environment, connection would fail if server isn't up.
    # For this demo script, fallback mock logic handles it.
    client = MCPClient()
    
    print("Connecting to Patent Agent via MCP (SSE)...")
    try:
        report = await client.compare_claims(
            claim_a="Method for A...", 
            claim_b="Method for A... with step B"
        )
        print("\nReport received via MCP:")
        print(report)
    except Exception as e:
        print(f"Connection failed (Ensure server is running): {e}")

if __name__ == "__main__":
    asyncio.run(main())
