from typing import List
import json
import re
from agents import Agent, Runner
from app.prompt.claim_feature_extract import SYSTEM_PROMPT, INSTRUCTIONS

class RuleBasedClaimFeatureExtractor:
    """
    Parses patent claims to extract features/limitations using rule-based splitting.
    """

    def __init__(self):
        pass

    async def extract_features(self, claim_text: str) -> List[str]:
        """
        Extracts features from a claim text by normalizing and splitting by semicolons.
        """
        # 1. Normalize text
        text = claim_text.strip()
        
        # 2. Identify the transition phrase (comprising, consisting of, etc.)
        if ":" in text:
            preamble, body = text.split(":", 1)
        else:
            body = text
            
        # 3. Split by semicolons
        raw_features = re.split(r';', body)
        
        features = []
        for feat in raw_features:
            # 4. Cleanup
            clean_feat = feat.strip()
            
            if clean_feat.endswith('.'):
                clean_feat = clean_feat[:-1]
            
            clean_feat = re.sub(r'^\s*(?:(?:\d+|[a-zA-Z])(?:\.|\))|(?:\([a-zA-Z0-9]+\)))\s*', '', clean_feat)
            clean_feat = re.sub(r'^\s*and\s+', '', clean_feat, flags=re.IGNORECASE)

            if clean_feat:
                features.append(clean_feat)
                
        return features


class LLMClaimFeatureExtractor:
    """
    Parses patent claims using an LLM to extract features.
    """
    
    def __init__(self):
        self.agent = Agent(
            name="ClaimFeatureExtractor",
            instructions=SYSTEM_PROMPT,
            model="gpt-4o"
        )

    async def extract_features(self, claim_text: str) -> List[str]:
        """
        Uses an LLM to extract features from the claim text.
        """
        prompt = INSTRUCTIONS.format(claim_text=claim_text)
        
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


if __name__ == "__main__":
    import sys
    import asyncio
    
    if len(sys.argv) < 2:
        print("Usage: python claim_parser.py <claim_file>")
        sys.exit(1)
    
    # Read claim text from file
    claim_file = sys.argv[1]
    with open(claim_file, 'r') as f:
        claim_text = f.read()
    
    # Parse the claim using rule-based parser
    parser = LLMClaimFeatureExtractor()
    features = asyncio.run(parser.extract_features(claim_text))
    
    print("Extracted Features:")
    for i, feature in enumerate(features, 1):
        print(f"{i}. {feature}")
