# Feature Comparator Skill

**ID**: `compare_features`
**Description**: Compares two lists of patent claim features to determine similarity.

## Inputs
- `features_a_json` (string): JSON list of features from the first claim.
- `features_b_json` (string): JSON list of features from the second claim.

## Output
- JSON object containing:
    - `overall_similarity` (float)
    - `matches` (list of match details)
    - `unmatched_b` (list of potential added matter)

## Tool Mapping
Maps to MCP Tool: `compare_features`
