import logging
import os
import uvicorn
import json

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from app.tools.mcp_tools.claim_analyzer import ClaimAnalyzer
from app.tools.mcp_tools.function_way_result import FunctionWayResultAnalyzer

server = Server("LLM Patent Analyzer")
claim_analyzer = ClaimAnalyzer()
function_way_result_analyzer = FunctionWayResultAnalyzer()

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="compare_claims",
            description="Compares two patent claim texts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_a": {"type": "string"},
                    "claim_b": {"type": "string"},
                },
                "required": ["claim_a", "claim_b"],
            },
        ),
        Tool(
            name="extract_features",
            description="Extracts a list of distinct features from a patent claim.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_text": {"type": "string"},
                },
                "required": ["claim_text"],
            },
        ),
        Tool(
            name="function_way_result_analysis",
            description="Analyzes the function way result of claims of a patent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claims": {
                        "type": "string",
                        "description": "Claims of a patent"
                    },
                },
                "required": ["claims"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent | ImageContent | EmbeddedResource]:
    if not arguments:
        return [TextContent(type="text", text="Missing arguments")]

    if name == "compare_claims":
        claim_a = arguments.get("claim_a", "")
        claim_b = arguments.get("claim_b", "")
        result = await claim_analyzer.compare_claims(claim_a, claim_b)
        return [TextContent(type="text", text=result)]
    
    elif name == "extract_features":
        text = arguments.get("claim_text", "")
        features = await claim_analyzer.claim_feature_extractor.extract_features(text)
        return [TextContent(type="text", text=json.dumps(features))]
        
    elif name == "function_way_result_analysis":
        claims = arguments.get("claims", "")
        try:
            result = await function_way_result_analyzer.analyze(claims)
            logging.info(f"FWR analyze() returned type={type(result).__name__}, value={str(result)[:200]}")
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logging.error(f"function_way_result_analysis FAILED: {e}\n{tb}")
            raise


# 2. SSE Transport Setup
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """Handle SSE connection requests"""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )
    # Return empty response to avoid NoneType error
    from starlette.responses import Response
    return Response()

# 3. Starlette App
app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
