import anthropic
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

schema = {
  "extracted_features": {
    "components": [],
    "functions": [],
    "effects": []
  },
  "canonical_mapping": [
    {
      "claim_feature": "",
      "cpc_canonical_keywords": [],
      "alternative_cpc_terms": [],
      "notes": ""
    }
  ],
  "primary_cpc_codes": [
    {
      "code": "",
      "description": "",
      "relevance": "",
      "coverage": "",
      "confidence": "",
      "rank": 1
    }
  ],
  "expanded_cpc_codes": [
    {
      "primary_code": "",
      "parent_subclass": {
        "code": "",
        "description": "",
        "related_main_groups": [
          {"code": "", "description": ""}
        ]
      },
      "sibling_subgroups": [
        {"code": "", "description": "", "relationship": ""}
      ],
      "child_subgroups": [
        {"code": "", "description": "", "relevance": ""}
      ],
      "cross_referenced_codes": [
        {"code": "", "description": "", "relationship": ""}
      ]
    }
  ],
  "keyword_expansion": [
    {
      "feature": "",
      "function_keywords": {
        "exact": [],
        "synonyms": [],
        "broader": [],
        "narrower": []
      },
      "way_keywords": {
        "exact": [],
        "alternatives": [],
        "variants": [],
        "related": []
      },
      "result_keywords": {
        "exact": [],
        "equivalents": [],
        "benefits": [],
        "performance": []
      }
    }
  ],
  "google_patent_queries": [
    {
      "query_number": 1,
      "strictness": "",
      "search_string": "",
      "strategy": "",
      "target": "",
      "estimated_recall": "",
      "estimated_precision": ""
    }
  ],
  "analysis_metadata": {
    "total_features_extracted": 0,
    "primary_cpc_count": 0,
    "expanded_cpc_count": 0,
    "total_keywords_generated": 0,
    "query_count": 10
  }
}

SYSTEM_PROMPT = """
You are an expert patent analyst with deep knowledge of patent free-to-operate (FTO) analysis using Cooperative Patent Classification (CPC). The analysis comprises the following 6 tasks
1. Extract claim features
2. Map features to CPC canonical keywords
3. Identify primary CPC codes
4. Expand CPC codes to related subgroups
5. Generate keyword expansion
6. Generate Google patent queries

## TASK 1: Extract Claim Features
Identify and extract all significant features from the claim:

1. **Technical Components**: Physical elements, devices, systems, materials, or apparatus
2. **Functional Elements**: Actions, operations, processes, or behaviors (focus on verbs and their objects)
3. **Technical Effects/Results**: Outcomes, advantages, or purposes achieved

Format as:
EXTRACTED FEATURES:
- Components: [list each component]
- Functions: [list each functional element with verb + object]
- Effects/Results: [list intended outcomes]

## TASK 2: Map Features to CPC Canonical Keywords
For each extracted feature, identify the standardized CPC terminology used in patent classification:

- Translate informal terms to formal CPC vocabulary
- Identify multiple canonical terms where applicable (synonyms used in CPC)
- Include both specific and general terminology levels

Present as:
CANONICAL MAPPING:
- Claim Feature
- CPC Canonical Keywords
- Alternative CPC Terms
- Notes

## TASK 3: Identify Primary CPC Codes
Determine the most directly relevant CPC codes for the claimed invention:

For each code provide:
- Full CPC code with all levels (class/subclass/group/subgroup)
- Complete official description
- Explanation of relevance to the claim
- Confidence level (High/Medium/Low)

Format as:
PRIMARY CPC CODES:
1. **[Full CPC Code]** - [Official Description]
   - Relevance: [detailed explanation]
   - Coverage: [which claim features this addresses]
   - Confidence: [High/Medium/Low]

Provide 5 primary codes ranked by relevance.

## TASK 4: Expand CPC Codes to Related Subgroups
For each primary CPC code identified, systematically expand to related codes:

**Expansion Strategy:**
1. **Parent Subclass Level**: Identify the subclass (e.g., B64C) and list other relevant main groups
2. **Sibling Groups**: Find related groups at the same hierarchical level
3. **Child Subgroups**: Drill down to more specific subgroup classifications
4. **Cross-References**: Include indexing codes and related subclasses referenced in CPC definitions

Format as:
EXPANDED CPC CODES:
- Primary Code
- Parent Subclass
- Sibling Subgroups
- Child Subgroups
- Cross-Referenced Codes

Provide this expansion for the top 3-5 most important primary codes.

## TASK 5: Expand Keywords - Functional Equivalents
Generate comprehensive keyword expansions based on Function-Way-Result analysis:

For each key technical feature, identify:

**FUNCTION Equivalents**: What purpose/goal does it serve?
- Alternative functions that achieve similar objectives
- Broader and narrower functional descriptions

**WAY Equivalents**: How is it implemented/achieved?
- Alternative mechanisms, methods, or approaches
- Different structural implementations
- Variant physical embodiments

**RESULT Equivalents**: What outcome is produced?
- Similar technical effects
- Equivalent performance characteristics
- Alternative benefit descriptions

Format as:
KEYWORD EXPANSION:

FEATURE: [Original Claim Feature]
- Function keywords
- Way keywords
- Result keywords


Provide this expansion for top 5 most important features.

## TASK 6: Generate Top 10 Google Patents Query Strings
Create 10 search queries ordered from MOST STRICT to MOST RELAXED:

**Query Construction Guidelines:**
- Use Google Patents advanced syntax:
  - CPC codes: CPC=B64C29/00
  - Multiple CPCs: (CPC=B64C27/00 OR CPC=B64C29/00)
  - Exact phrases: "vertical takeoff"
  - Wildcards: elect* motor (matches electric, electrical, electromechanical)
  - Boolean: AND, OR, NOT
  - Proximity: Use phrases for terms that should appear near each other

**Strictness Ordering:**
1-2: Most strict - All core features + specific CPCs + exact terminology
3-4: High strict - Core features + primary CPCs + some variations
5-6: Medium strict - Key features + expanded CPCs + functional equivalents
7-8: Low strict - Broader features + subclass CPCs + wide keyword variations
9-10: Most relaxed - General problem area + broad CPCs + alternative approaches

Format each query as:
**Query [N]** (Strictness: [MOST STRICT / HIGH / MEDIUM / LOW / MOST RELAXED])
Search String: [complete Google Patents query]

Strategy: [1-2 sentence explanation of query logic]
Target: [what types of patents this should find]
Estimated Recall: [High/Medium/Low - how many relevant patents expected]
Estimated Precision: [High/Medium/Low - how focused the results will be]


## OUTPUT FORMAT
Provide your complete analysis in valid JSON format:
```json
{schema_json_string}
```


Please analyze the following patent claim following the above instructions.
{claim_text}

"""

claim_text = """
1. An aircraft comprising:
a boom;
a propulsion assembly coupled to a first end of the boom, wherein the propulsion assembly comprises a plurality of rotor blades surrounding by a shroud;
a plurality of paddles disposed between the plurality of rotor blades and the boom; and
a first wing coupled to a second end of the boom via a first rotating joint for rotating the first wing about an axis through a length of the first wing; and
a second rotating joint coupled to the first end of the boom, the second rotating joint is configured to accommodate rotation of the propulsion assembly with respect to the boom to transition the aircraft from vertical flight to horizontal flight.
2. The aircraft of claim 1, wherein the first wing is configured to move between a first position, wherein the first wing is folded substantially parallel with the boom, and a second position, wherein the first wing is unfolded from the boom.
3. The aircraft of claim 1, further comprising an electrical energy source disposed in the boom, wherein the propulsion assembly is powered by the electrical energy source.
4. The aircraft of claim 1, further comprising a payload connector coupled to the second end of the boom via the first rotating joint.
5. The aircraft of claim 1, wherein the propulsion assembly further comprises a plurality of stator vanes surrounded by the shroud.
6. The aircraft of claim 1, further comprising a stanchion, wherein the plurality of paddles are configured to rotate about the stanchion to modify a direction that moving air is displaced relative to the boom.
7. The aircraft of claim 6, wherein the plurality of paddles comprises:
a first paddle configured to rotate about an axis through a length of the first paddle; and
a second paddle configured to rotate about an axis through a length of the second paddle.
8. The aircraft of claim 6, wherein the plurality of paddles are configured to spin the boom about an axis through a length of the boom in vertical flight.
9. The aircraft of claim 1, further comprising a second wing coupled to the first end of the boom via the second rotating joint, wherein the second rotating joint is configured to rotate the second wing about an axis through a length of the second wing.
10. The aircraft of claim 9, wherein the second wing is configured to move between a first position, wherein the second wing is folded substantially parallel with the boom, and a second position, wherein the second wing is unfolded from the boom.
11. An aircraft comprising:
a boom;
a propulsion assembly coupled to a first end of the boom;
a first wing coupled to a second end of the boom via a first rotating joint for rotating the first wing about an axis through a length of the first wing; and
a second wing coupled to the first end of the boom via a second rotating joint for rotating the second wing about an axis through a length of the second wing;
wherein the boom is configured to be suspended substantially vertically from the propulsion assembly with the aircraft in a vertical flight mode; and
the first wing and the second wing are configured to rotate together with the boom when the aircraft is in vertical flight.
12. The aircraft of claim 11, wherein the first wing and the second wing are configured to move between first positions, wherein the first wing and the second wing are folded substantially parallel with the boom, and second positions, wherein the first wing and the second wing are unfolded from the boom and oriented substantially perpendicular to the boom.
13. The aircraft of claim 12, wherein, during vertical flight mode, the propulsion assembly is configured to generate a vertical thrust; and
the second rotating joint is configured to rotate the propulsion assembly with respect to the boom to generate a horizontal thrust with the propulsion assembly to transition the aircraft from the vertical flight mode to a horizontal flight mode.
14. The aircraft of claim 13, wherein, during the horizontal flight mode, the first wing and the second wing are configured to generate lift for the aircraft while the propulsion assembly generates the horizontal thrust.
15. The aircraft of claim 14, wherein the first wing and the second wing are configured to be unfolded from the boom toward the second positions as the aircraft transitions from the vertical flight mode to the horizontal flight mode.
16. The aircraft of claim 15, wherein the boom is configured to be oriented in a substantially horizontal position in the horizontal flight mode.
17. The aircraft of claim 12, wherein the first wing and the second wing are independently moveable with respect to one another.
18. The aircraft of claim 12, further comprising:
a third wing coupled to the second end of the boom via the first rotating joint for rotating the third wing about an axis through a length of the third wing, wherein the third wing is disposed opposite the first rotating joint from the first wing; and
a fourth wing coupled to the first end of the boom via the second rotating joint for rotating the fourth wing about an axis through a length of the fourth wing, wherein the fourth wing is disposed opposite the second rotating joint from the first wing.
19. An aircraft comprising:
a boom housing an electrical energy source;
a propulsion assembly coupled to a first end of the boom;
a first wing coupled to a second end of the boom via a first rotating joint; and
a payload connector coupled to the second end of the boom via the first rotating joint;
wherein the payload connector is rotatable with respect to the boom via the first rotating joint, the payload connector is configured to connect to a payload while the aircraft is in flight, and the payload connector comprises an electrical connection whereby electrical energy can be transferred between the electrical energy source and the payload during flight.
20. The aircraft of claim 19, wherein the payload connector comprises an airfoil shaped portion configured to operate as a rudder during flight of the aircraft.
"""

if __name__ == "__main__":
    prompt = SYSTEM_PROMPT.format(schema_json_string=json.dumps(schema), claim_text=claim_text)
    print(prompt)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    print(message.content[0].text)