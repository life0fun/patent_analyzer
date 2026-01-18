from .claim_parser import LLMClaimParser, RuleBasedClaimParser
from .feature_comparator import FeatureComparator, LLMFeatureComparator

class ClaimAnalyzer:
    """
    Orchestrates the patent claim comparison process.
    """
    
    def __init__(self, parser_type: str = "llm", comparator_type: str = "llm"):
        if parser_type == "llm":
            self.claim_parser = LLMClaimParser()
        else:
            self.claim_parser = RuleBasedClaimParser()
        
        if comparator_type == "llm":
            self.feature_comparator = LLMFeatureComparator()
        else:
            self.feature_comparator = FeatureComparator()

    async def compare_claims(self, claim_text_a: str, claim_text_b: str) -> str:
        """
        Analyzes two claims and returns a human-readable report.
        """
        features_a = await self.claim_parser.extract_features(claim_text_a)
        features_b = await self.claim_parser.extract_features(claim_text_b)
        
        print(f"DEBUG: claim A features: {features_a}")
        print(f"DEBUG: claim B features: {features_b}")
        
        result = await self.feature_comparator.compare(features_a, features_b)
        
        report = []
        report.append("# Patent Claim Comparison Report\n")
        report.append(f"**Overall Similarity Score**: {result['overall_similarity']:.2f}\n")
        
        report.append("## Feature Matches\n")
        for match in result['matches']:
            report.append(f"- **Score**: {match['score']:.2f}")
            report.append(f"  - Claim A: {match['feature_a']}")
            report.append(f"  - Claim B: {match['feature_b']}")
            report.append("")
            
        if result['unmatched_b']:
            report.append("## Unmatched Features in Claim B (Potential Added Matter)\n")
            for feat in result['unmatched_b']:
                report.append(f"- {feat}")
        
        return "\n".join(report)
