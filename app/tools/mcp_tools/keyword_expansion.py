from typing import List
import json
import re
from agents import Agent, Runner
from app.db.db import init_db
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

    async def expand_keywords(self, keyword: str) -> str:
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
            return json.dumps(expanded_keywords)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return response_text


if __name__ == "__main__":
    import sys
    import asyncio
    # Save features to database
    conn = init_db()
    cursor = conn.cursor()
    
    if len(sys.argv) < 2:
        cursor.execute("SELECT id, keyword, feature_id FROM keywords")
        features = cursor.fetchall()
        if not features:
            print("No features found in the database.")
            print("Usage: python keyword_expander.py <keyword>")
            sys.exit(1)
        keyword_id = features[0][0]
        keyword = features[0][1]
    else:
        # Read claim text from file
        keyword_id = None
        keyword = sys.argv[1]
    
    expander = LLMKeywordExpander()
    expanded_keywords = asyncio.run(expander.expand_keywords(keyword))
    
    print(f"Expanded Keywords: {expanded_keywords}")
    
    # Save features to database
    expanded_keywords_json = json.loads(expanded_keywords)
    ipc_cpc_code = expanded_keywords_json["IPCCPCcode"]
    rationale = expanded_keywords_json["Rationale"]
    expanded_keywords = expanded_keywords_json["ExpandedKeywords"]
    cursor.execute("INSERT INTO expanded_keywords (keyword_id, keyword, expanded_keywords, ipc_cpc_code, rationale) VALUES (?, ?, ?, ?, ?)", (keyword_id, keyword, json.dumps(expanded_keywords), ipc_cpc_code, rationale))
    
    conn.commit()
    conn.close()
