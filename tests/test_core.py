from src.graph_loader import load_graph
from src.impact_engine import analyze_impact, find_impacted
from src.llm_reasoner import _fallback_analysis


def test_load_graph_creates_expected_nodes():
    graph = load_graph()
    assert graph.number_of_nodes() == 18
    assert graph.number_of_edges() == 22
    assert "api-gateway" in graph.nodes


def test_find_impacted_for_auth_service():
    graph = load_graph()
    impacted = find_impacted(graph, "auth-service")
    assert "api-gateway" in impacted
    assert impacted["api-gateway"]["hops"] == 1
    assert impacted["api-gateway"]["path"] == ["api-gateway", "auth-service"]


def test_analyze_impact_and_fallback_report():
    graph = load_graph()
    incidents = [{"id": "INC-4471", "affected_components": ["auth-service", "user-service", "api-gateway"]}]
    impacts = analyze_impact(graph, "auth-service", incidents)
    assert any(item["component"] == "api-gateway" for item in impacts)

    report = _fallback_analysis(
        {"component": "auth-service", "field": "token_expiry_hours", "old_value": 24, "new_value": 1},
        [
            {
                "component": "api-gateway",
                "risk": "High",
                "hops": 1,
                "edge_type": "sync_call",
                "criticality": "high",
                "path": "api-gateway -> auth-service",
            }
        ],
        {},
    )
    assert report["impacts"][0]["component"] == "api-gateway"
    assert "Deploy" in report["overall_recommendation"]
