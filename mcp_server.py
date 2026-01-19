import logging
import uvicorn
import json

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from app.tools.mcp_tools.claim_analyzer import ClaimAnalyzer

server = Server("LLM Patent Analyzer")
claim_analyzer = ClaimAnalyzer()

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
            name="compare_features",
            description="Compares two lists of features.",
            inputSchema={
                "type": "object",
                "properties": {
                    "features_a": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of features from Claim A"
                    },
                    "features_b": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of features from Claim B"
                    },
                },
                "required": ["features_a", "features_b"],
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
        features = await claim_analyzer.parser.extract_features(text)
        return [TextContent(type="text", text=json.dumps(features))]
        
    elif name == "compare_features":
        def parse_features(val):
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except:
                    return [val]
            return []

        try:
            feats_a = parse_features(arguments.get("features_a", []))
            feats_b = parse_features(arguments.get("features_b", []))
            result = await claim_analyzer.feature_comparator.compare(feats_a, feats_b)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error parsing features: {e}")]

    return [TextContent(type="text", text="Unknown tool")]


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
