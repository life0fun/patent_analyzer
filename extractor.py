from typing import List
import json
from agents import Agent, Runner

class FeatureExtractor:
    def __init__(self):
        self.agent = Agent(
            name="FeatureExtractor",
            instructions="You are an expert patent attorney. Your task is to extract independent technical features from the patent claim provided.",
            model="gpt-4o"
        )

    async def extract_features(self, claim_text: str) -> List[str]:
        prompt = f"""
        Extract independent technical features from the following patent claim.
        List each technical feature separately. Do not include preamble unless it contains essential limitations.
        Return the result as a raw JSON list of strings.
        
        Claim:
        {claim_text}
        
        JSON Output:
        """

        result = await Runner.run(self.agent, prompt)
        response_text = result.final_output
        
        try:
            # Clean up potential markdown formatting (```json ... ```)
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            features = json.loads(clean_json)
            if isinstance(features, list):
                return [str(f) for f in features]
            else:
                return [str(features)]
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return [line.strip() for line in response_text.splitlines() if line.strip()]
