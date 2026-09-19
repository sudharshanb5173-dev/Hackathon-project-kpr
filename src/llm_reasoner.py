import json
import os
from openai import OpenAI

def build_prompt(change, impacts, evidence_map):
    impact_lines = []
    for imp in impacts:
        ev = evidence_map.get(imp["component"], [])
        ev_text = "\n".join([f"  - {e['id']}: {e['title']} (root cause: {e['root_cause']})" for e in ev]) or "  - None"
        impact_lines.append(
            f"- {imp['component']} (risk={imp['risk']}, hops={imp['hops']}, "
            f"criticality={imp['criticality']}, path={imp['path']})\n"
            f"  Historical evidence:\n{ev_text}"
        )
    
    impacts_text = "\n".join(impact_lines)
    
    prompt = f"""You are an expert engineering change impact analyst.

PROPOSED CHANGE:
- Component: {change['component']}
- Field: {change['field']}
- Old value: {change['old_value']}
- New value: {change['new_value']}

IMPACTED COMPONENTS (already computed):
{impacts_text}

For EACH impacted component, explain:
1. WHY it is affected (the dependency chain in plain English)
2. WHAT could specifically go wrong (failure mode)
3. EVIDENCE supporting this (cite incidents or configs)
4. RECOMMENDATION for this component

Then give an OVERALL recommendation.

Return ONLY valid JSON in this exact schema:
{{
  "impacts": [
    {{
      "component": "...",
      "risk": "High|Medium|Low",
      "reasoning": "...",
      "failure_mode": "...",
      "evidence": ["...", "..."],
      "recommendation": "..."
    }}
  ],
  "overall_recommendation": "..."
}}
"""
    return prompt

def analyze_with_llm(change, impacts, evidence_map, api_key=None):
    import os
    from openai import OpenAI
    
    api_key = api_key or os.getenv("OLLAMA_API_KEY")
    
    if not api_key:
        return _fallback_analysis(change, impacts, evidence_map)
    
    # Point to Ollama Cloud instead of OpenAI
    client = OpenAI(
        base_url="https://ollama.com/v1",
        api_key=api_key
    )
    
    prompt = build_prompt(change, impacts, evidence_map)
    
    response = client.chat.completions.create(
        model="gemma4:31b",          # ← pick a model from Ollama's cloud
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    import json
    return json.loads(response.choices[0].message.content)

def _fallback_analysis(change, impacts, evidence_map):
    """Works without an API key — good for testing."""
    results = []
    for imp in impacts:
        ev = evidence_map.get(imp["component"], [])
        evidence = [f"{e['id']}: {e['title']}" for e in ev] or ["No historical incidents found"]
        
        reasoning = (
            f"{imp['component']} depends on {change['component']} via {imp['edge_type']} "
            f"({imp['hops']} hop(s) away). Path: {imp['path']}."
        )
        failure_mode = (
            f"Changing {change['field']} may cause {imp['component']} to experience "
            f"timeouts, errors, or degraded performance."
        )
        recommendation = f"Monitor {imp['component']} closely during rollout; consider canary deployment."
        
        results.append({
            "component": imp["component"],
            "risk": imp["risk"],
            "reasoning": reasoning,
            "failure_mode": failure_mode,
            "evidence": evidence,
            "recommendation": recommendation
        })
    
    return {
        "impacts": results,
        "overall_recommendation": (
            f"Change to {change['component']}.{change['field']} affects "
            f"{len(impacts)} components. Deploy to staging first, use canary rollout, "
            f"and monitor high-risk components closely."
        )
    }
