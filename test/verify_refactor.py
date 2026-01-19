import asyncio
import json
from analyzer import LLMAnalyzer

async def verify_refactor():
    print("Testing Asynchronous Patent Agent Logic...")
    
    # Initialize analyzer (it uses LLMClient)
    analyzer = LLMAnalyzer()
    
    claim_a = "A method for controlling an unmanned aerial vehicle (UAV), comprising: receiving a first signal from a remote controller."
    claim_b = "A method for operating a drone, comprising: receiving a command signal from a user device."
    
    print("\nRunning analyze()...")
    # This should now be awaited
    try:
        report = await analyzer.analyze(claim_a, claim_b)
        print("\nSUCCESS: Report generated without AgentRunner error.")
        print("-" * 20)
        print(report[:200] + "...") 
    except Exception as e:
        print(f"\nFAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(verify_refactor())
