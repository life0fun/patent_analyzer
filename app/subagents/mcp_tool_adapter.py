from typing import Any, Dict, Callable
import json
from agents import FunctionTool

def adapt_mcp_tool(mcp_tool_name: str, mcp_tool_description: str, mcp_tool_schema: Dict[str, Any], executor: Callable) -> FunctionTool:
    """
    Creates a FunctionTool compatible with the Agent's tools parameter
    based on an MCP tool definition.
    """
    
    async def dynamic_tool_handler(*args, **kwargs):
        """
        Dynamic handler that forwards calls to the executor.
        """
        # print(f"DEBUG: dynamic_tool_handler called for {mcp_tool_name} with args: {args} (types: {[type(a) for a in args]}), kwargs: {kwargs}")
        
        # Helper to try parsing argument as tool input
        def parse_arg(arg):
             if isinstance(arg, dict):
                 return arg
             if isinstance(arg, str):
                 try:
                     parsed = json.loads(arg)
                     if isinstance(parsed, dict):
                         return parsed
                 except json.JSONDecodeError:
                     pass
             return None

        tool_input = kwargs.copy()

        # Try to find the tool input in args
        if args and not tool_input:
             # Iterate through args to find the payload
             for arg in args:
                 # Skip ToolContext (we check by type name or just if it's not dict/str/json)
                 # Actually, parse_arg checks for dict/str. assertions of ToolContext will fail parse_arg unless it looks like dict (it doesn't).
                 found = parse_arg(arg)
                 if found:
                     tool_input = found
                     # print(f"DEBUG: Found tool input in args: {tool_input}")
                     break
            
             if not tool_input:
                # If we still didn't find a dict/json, maybe it IS positional args mapping (but we have ToolContext in the way)
                # If we have ToolContext, we should skip it.
                # Assuming ToolContext is NOT a primitive type we expect.
                
                # Filter out ToolContext-like objects (checking if it is primitive)
                clean_args = [a for a in args if isinstance(a, (str, int, float, bool, list, dict, type(None)))]
                
                # Assume remaining args correspond to properties in order
                props = list(mcp_tool_schema.get("properties", {}).keys())
                if clean_args and len(clean_args) <= len(props):
                    for i, arg in enumerate(clean_args):
                        tool_input[props[i]] = arg
                    # print(f"DEBUG: Mapped filtered positional args to: {tool_input}")
                else:
                     # print(f"DEBUG: Could not map args. clean_args={clean_args}")
                     pass
        
        print(f"DEBUG: Calling executor with tool name: {mcp_tool_name}, tool_input: {tool_input}")
        result = await executor(mcp_tool_name, tool_input)
        print(f"DEBUG: dynamic_tool_handler result: {result}")
        return str(result)

    # Sanitize schema for Agent compatibility
    sanitized_schema = mcp_tool_schema.copy()
    if "additionalProperties" in sanitized_schema:
        del sanitized_schema["additionalProperties"]
    if "title" in sanitized_schema:
        del sanitized_schema["title"]

    # Instantiate FunctionTool directly to ensure schema is respected
    # and not inferred from the generic handler signature.
    return FunctionTool(
        name=mcp_tool_name,
        description=mcp_tool_description,
        params_json_schema=sanitized_schema,
        on_invoke_tool=dynamic_tool_handler,
        strict_json_schema=False # Match the strict_mode=False behavior we wanted
    )
