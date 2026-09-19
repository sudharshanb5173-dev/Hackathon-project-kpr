import networkx as nx
from .graph_loader import load_graph

CRITICALITY_SCORE = {"critical": 30, "high": 20, "medium": 10, "low": 0}

def find_impacted(G, changed_component, max_hops=3):
    """Find all components that depend on changed_component."""
    impacted = {}
    for node in G.nodes:
        if node == changed_component:
            continue
        try:
            # We want: does 'node' depend on 'changed_component'?
            # path from node -> changed_component
            path = nx.shortest_path(G, source=node, target=changed_component)
            hops = len(path) - 1
            if hops <= max_hops:
                edge = G[path[-2]][path[-1]]
                impacted[node] = {
                    "hops": hops,
                    "path": path,
                    "edge_criticality": edge.get("criticality", "soft"),
                    "edge_type": edge.get("type", "unknown")
                }
        except nx.NetworkXNoPath:
            continue
    return impacted

def risk_score(hops, edge_crit, node_crit, incident_hits=0):
    score = (4 - hops) * 10
    score += 20 if edge_crit == "hard" else 5
    score += CRITICALITY_SCORE.get(node_crit, 0)
    score += incident_hits * 15
    return score

def classify(score):
    if score >= 60: return "High"
    if score >= 30: return "Medium"
    return "Low"

def analyze_impact(G, changed_component, incidents):
    impacted = find_impacted(G, changed_component)
    results = []
    
    for comp, info in impacted.items():
        # Count how many past incidents mention this component
        hits = sum(1 for inc in incidents if comp in inc["affected_components"])
        
        node_crit = G.nodes[comp].get("criticality", "medium")
        score = risk_score(info["hops"], info["edge_criticality"], node_crit, hits)
        
        results.append({
            "component": comp,
            "risk": classify(score),
            "score": score,
            "hops": info["hops"],
            "path": " -> ".join(info["path"]),
            "edge_type": info["edge_type"],
            "criticality": node_crit,
            "incident_hits": hits
        })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
