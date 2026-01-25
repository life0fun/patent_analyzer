from typing import List
import json
import re
from agents import Agent, Runner
from app.prompt.keyword_expansion import SYSTEM_PROMPT, INSTRUCTIONS

class RuleBasedKeywordExpander:
    """
    Parses patent claims to extract features/limitations using rule-based splitting.
    """

    def __init__(self):
        pass

    async def expand_keywords(self, keyword: str) -> List[str]:
        """
        Extracts features from a claim text by normalizing and splitting by semicolons.
        """
        # 1. Normalize text
        keyword = keyword.strip()
        
        expanded_keywords = []
        return expanded_keywords


class LLMKeywordExpander:
    """
    Parses patent claims using an LLM to extract features.
    """
    
    def __init__(self):
        self.agent = Agent(
            name="KeywordExpander",
            instructions=SYSTEM_PROMPT,
            model="gpt-4o"
        )

    async def expand_keywords(self, keyword: str) -> List[str]:
        """
        Uses an LLM to extract features from the claim text.
        """
        prompt = INSTRUCTIONS.format(keyword=keyword)
        
        result = await Runner.run(self.agent, prompt)
        response_text = result.final_output
        
        try:
            # Clean up potential markdown formatting (```json ... ```)
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            expanded_keywords = json.loads(clean_json)
            if isinstance(expanded_keywords, list):
                return [str(f) for f in expanded_keywords]
            else:
                return [str(expanded_keywords)]
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return [line.strip() for line in response_text.splitlines() if line.strip()]


if __name__ == "__main__":
    import sys
    import asyncio
    
    if len(sys.argv) < 2:
        print("Usage: python keyword_expander.py <keyword>")
        sys.exit(1)
    
    # Read claim text from file
    keyword = sys.argv[1]
    
    expander = LLMKeywordExpander()
    expanded_keywords = asyncio.run(expander.expand_keywords(keyword))
    
    print("Expanded Keywords:")
    for i, keyword in enumerate(expanded_keywords, 1):
        print(f"{i}. {keyword}")
