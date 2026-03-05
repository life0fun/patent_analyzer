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
    
    async def analyze(self, claim_text: str) -> Dict:
        """
        Performs a granular "Function-Way-Result" (FWR) decomposition of the provided patent claims.
        """
        if not claim_text:
            return {}
        
        prompt = INSTRUCTIONS.format(claim_text=claim_text)
        
        result = await Runner.run(self.agent, prompt)
        response_text = result.final_output
        
        try:
            # Clean up potential markdown formatting
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            result_dict = json.loads(clean_json)
            
            # Validate and normalize the result
            if not isinstance(result_dict, dict):
                raise ValueError("LLM response is not a dictionary")
            
            return result_dict
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to parse LLM response: {e}")
            print(f"Raw response: {response_text}")
            