from typing import List, Dict, Set
import json
from agents import Agent, Runner

class FeatureComparator:
    """
    Compares lists of text features to find similarities using pure Python (Jaccard Similarity).
    """
    
    def __init__(self):
        pass

    def _tokenize(self, text: str) -> Set[str]:
        """Simple tokenizer that splits by whitespace and lowercases."""
        return set(text.lower().split())

    def _jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Calculates Jaccard similarity between two texts."""
        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)
        
        if not tokens_a and not tokens_b:
            return 1.0
        if not tokens_a or not tokens_b:
            return 0.0
            
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        
        return len(intersection) / len(union)

    async def compare(self, features_a: List[str], features_b: List[str]) -> Dict:
        """
        Compares two lists of features and returns a mapping and similarity scores.
        """
        if not features_a or not features_b:
            return {
                "matches": [],
                "overall_similarity": 0.0,
                "unmatched_a": features_a,
                "unmatched_b": features_b
            }

        matches = []
        matched_indices_b = set()
        
        # For each feature in A, find the best match in B
        for feat_a in features_a:
            best_score = -1.0
            best_match_idx = -1
            best_feat_b = ""
            
            for i, feat_b in enumerate(features_b):
                score = self._jaccard_similarity(feat_a, feat_b)
                if score > best_score:
                    best_score = score
                    best_match_idx = i
                    best_feat_b = feat_b
            
            # Use a threshold to consider it a match? For now, just report the best one found.
            if best_match_idx != -1:
                matches.append({
                    "feature_a": feat_a,
                    "feature_b": best_feat_b,
                    "score": float(best_score)
                })
                matched_indices_b.add(best_match_idx)
            else:
                 matches.append({
                    "feature_a": feat_a,
                    "feature_b": None,
                    "score": 0.0
                })

        # Overall similarity: average of best matches
        overall_similarity = sum(m["score"] for m in matches) / len(matches) if matches else 0.0
        
        # Identify unmatched B features (those that were never the *best* match for any A)
        # Note: This logic allows multiple A's to map to the same B.
        unmatched_b = [f for i, f in enumerate(features_b) if i not in matched_indices_b]
        
        return {
            "matches": matches,
            "overall_similarity": overall_similarity,
            "unmatched_a": [], 
            "unmatched_b": unmatched_b 
        }


class LLMFeatureComparator:
    """
    Compares lists of text features using an LLM for semantic understanding.
    """
    
    def __init__(self):
        self.agent = Agent(
            name="FeatureComparator",
            instructions="You are an expert patent agent. Your task is to compare two lists of patent claim features and determine their semantic similarity.",
            model="gpt-4o"
        )
    
    async def compare(self, features_a: List[str], features_b: List[str]) -> Dict:
        """
        Compares two lists of features using LLM and returns mapping and similarity scores.
        """
        if not features_a or not features_b:
            return {
                "matches": [],
                "overall_similarity": 0.0,
                "unmatched_a": features_a,
                "unmatched_b": features_b
            }
        
        prompt = f"""
        Compare the following two lists of patent claim features and determine their semantic similarity.

        Features from Claim A:
        {json.dumps(features_a, indent=2)}

        Features from Claim B:
        {json.dumps(features_b, indent=2)}

        For each feature in Claim A, find the best matching feature in Claim B (if any) and assign a similarity score from 0.0 to 1.0.
        - 1.0 means identical or equivalent in meaning
        - 0.7-0.9 means very similar with minor differences
        - 0.4-0.6 means somewhat related
        - 0.0-0.3 means different or unrelated

        Return a JSON object with this structure:
        {{
          "matches": [
            {{
              "feature_a": "text of feature from A",
              "feature_b": "text of best matching feature from B or null if no good match",
              "score": 0.85,
              "explanation": "brief explanation of the match"
            }}
          ],
          "overall_similarity": 0.75,
          "unmatched_a": [],
          "unmatched_b": ["features from B that weren't matched"]
        }}

        JSON Output:
        """
        
        result = await Runner.run(self.agent, prompt)
        response_text = result.final_output
        
        try:
            # Clean up potential markdown formatting
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            result_dict = json.loads(clean_json)
            
            # Validate and normalize the result
            if not isinstance(result_dict, dict):
                raise ValueError("LLM response is not a dictionary")
            
            # Ensure required keys exist
            result_dict.setdefault("matches", [])
            result_dict.setdefault("overall_similarity", 0.0)
            result_dict.setdefault("unmatched_a", [])
            result_dict.setdefault("unmatched_b", [])
            
            return result_dict
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to parse LLM response: {e}")
            print(f"Raw response: {response_text}")
            # Fallback to rule-based comparison
            fallback = FeatureComparator()
            return await fallback.compare(features_a, features_b)
