import asyncio
from agents import Agent, Runner, function_tool, OpenAIConversationsSession, StopAtTools, ToolOutputText

@function_tool
def my_tool(x: int):
    return x * 2

agent = Agent(
    name="TestAgent",
    instructions="You have a tool 'my_tool'. Use it to calculate double of the input number. When you have the answer, say 'FINAL: <answer>'.",
    tools=[my_tool],
    model="gpt-4o",
    tool_use_behavior=StopAtTools()
)

async def main():
    session = OpenAIConversationsSession()
    print("--- Turn 1 ---")
    # Initial request
    result = await Runner.run(agent, "Double 5", session=session)
    print("Output:", result.final_output)
    print("Result attributes:", dir(result))
    
    # Check if there are tool calls to process - 'tool_calls' might be in a different attribute or the return type is distinct when stopped.
    # Looking at prior agent lib dump: RunResult seems standard.
    # Maybe it's 'output' list if it's streamed? But run() returns RunResult which has final_output maybe?
    # Let's verify what result holds.
    print("\n--- Executing Tool (Simulated) ---")
    # outputs = []
    # for call in result.tool_calls:
    #     print(f"Calling {call.function.name} with {call.function.arguments}")
    #     val = call.function.arguments['x']
    #     res = my_tool(val) 
    #     outputs.append(ToolOutputText(tool_call_id=call.id, content=str(res)))
            
    print("\n--- Turn 2 (Feeding back result) ---")
    # Feed back tool output
    # result2 = await Runner.run(agent, outputs, session=session)
    # print("Output 2:", result2.final_output)

if __name__ == "__main__":
    asyncio.run(main())
