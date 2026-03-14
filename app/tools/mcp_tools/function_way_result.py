from typing import List, Dict, Set
import json
from agents import Agent, Runner
from app.prompt.function_way_result import SYSTEM_PROMPT, INSTRUCTIONS  


class FunctionWayResultAnalyzer:
    """
    Compares lists of text features using an LLM for semantic understanding.
    """
    
    def __init__(self):
        self.agent = Agent(
            name="FunctionWayResultAnalyzer",
            instructions=SYSTEM_PROMPT,
            model="gpt-4o"
        )
    
    async def analyze(self, claims: str) -> list | dict:
        """
        Performs a granular "Function-Way-Result" (FWR) decomposition of the provided patent claims.
        Returns a list of FWR component dicts (or a dict if the LLM returns one).
        """
        if not claims:
            return []
        
        prompt = INSTRUCTIONS.format(claims=claims)
        
        try:
            result = await Runner.run(self.agent, prompt)
            response_text = result.final_output
        except Exception as e:
            import traceback
            print(f"ERROR: Runner.run failed: {e}\n{traceback.format_exc()}")
            raise
        
        try:
            # Clean up potential markdown formatting
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            result_obj = json.loads(clean_json)
            
            # Accept both list (array of FWR elements) and dict
            if isinstance(result_obj, (list, dict)):
                print(f"----- MCP FWR analysis returns type={type(result_obj).__name__}, {len(result_obj)} items")
                return result_obj
            else:
                raise ValueError(f"LLM response is neither list nor dict: {type(result_obj)}")
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to parse LLM response: {e}")
            print(f"Raw response: {response_text}")
            raise

            