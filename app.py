import streamlit as st
import os
from collections import deque
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.graph_loader import load_graph
from src.impact_engine import analyze_impact
from src.evidence_retriever import init_incident_store, get_evidence
from src.llm_reasoner import analyze_with_llm

st.set_page_config(page_title="Change Impact Analyzer", layout="wide")
st.title("🔍 Engineering Change Impact Analyzer")
st.caption("Predict what a change will break — before you deploy it.")

# Load everything (cached so it doesn't reload every click)
@st.cache_resource
def load_all():
    G = load_graph()
    collection, incidents = init_incident_store()
    return G, collection, incidents

G, collection, incidents = load_all()

# ---------- SIDEBAR: Input Form ----------
st.sidebar.header("Proposed Change")

ai_available = bool(os.getenv("OLLAMA_API_KEY") or os.getenv("OPENAI_API_KEY"))
ai_agent_enabled = st.sidebar.toggle("Enable AI agent", value=ai_available)
if ai_available:
    st.sidebar.caption("AI agent: LLM reasoning enabled")
else:
    st.sidebar.caption("AI agent: fallback reasoning mode")

components = sorted(G.nodes)
component = st.sidebar.selectbox("Component to change", components)

# Show current config of selected component
current_config = G.nodes[component].get("config", {})
if current_config:
    st.sidebar.write("**Current config:**")
    for k, v in current_config.items():
        st.sidebar.write(f"- `{k}` = `{v}`")
    field = st.sidebar.selectbox("Field to change", list(current_config.keys()))
    old_value = current_config[field]
    st.sidebar.write(f"Old value: `{old_value}`")
    new_value = st.sidebar.text_input("New value", value=str(old_value))
else:
    st.sidebar.warning("This component has no config to change.")
    field = st.sidebar.text_input("Field name")
    old_value = ""
    new_value = st.sidebar.text_input("New value")

analyze_btn = st.sidebar.button("🚀 Analyze Impact", type="primary")

def build_impact_tree(G, changed_component, impacted_components):
    """Build a tree-style impact view rooted at the changed component."""
    if not impacted_components:
        return None

    tree = nx.DiGraph()
    tree.add_node(changed_component)
    parent_map = {changed_component: None}

    for comp in impacted_components:
        try:
            path = nx.shortest_path(G, source=changed_component, target=comp)
        except nx.NetworkXNoPath:
            path = [changed_component, comp]

        for parent, child in zip(path, path[1:]):
            if child not in parent_map:
                tree.add_edge(parent, child)
                parent_map[child] = parent

    if tree.number_of_nodes() == 1:
        return None

    levels = {changed_component: 0}
    queue = deque([changed_component])
    while queue:
        node = queue.popleft()
        for child in list(tree.successors(node)):
            if child not in levels:
                levels[child] = levels[node] + 1
                queue.append(child)

    # Keep siblings in the same level ordered by name for stable tree layout.
    nodes_by_level = {}
    for node, level in levels.items():
        nodes_by_level.setdefault(level, []).append(node)
    for level in nodes_by_level:
        nodes_by_level[level].sort()

    pos = {}
    for level, nodes in sorted(nodes_by_level.items()):
        total = len(nodes)
        for idx, node in enumerate(nodes):
            pos[node] = (level, idx - (total - 1) / 2)

    fig, ax = plt.subplots(figsize=(12, 7))
    node_colors = []
    for node in tree.nodes:
        if node == changed_component:
            node_colors.append("#ff6b6b")
        elif node in impacted_components:
            node_colors.append("#4dabf7")
        else:
            node_colors.append("#dfe6e9")

    nx.draw_networkx_edges(
        tree,
        pos,
        edge_color="#7b8794",
        width=1.8,
        alpha=0.8,
        arrows=True,
        arrowstyle="-|>",
        ax=ax,
    )
    nx.draw_networkx_nodes(
        tree,
        pos,
        node_color=node_colors,
        node_size=1100,
        edgecolors="black",
        linewidths=1.1,
        ax=ax,
    )
    nx.draw_networkx_labels(tree, pos, font_size=9, ax=ax)

    ax.set_title("AI agent impact tree")
    ax.set_axis_off()
    fig.tight_layout()
    return fig


# ---------- MAIN AREA ----------
if analyze_btn:
    change = {
        "component": component,
        "field": field,
        "old_value": old_value,
        "new_value": new_value
    }
    
    with st.spinner("Analyzing dependencies..."):
        impacts = analyze_impact(G, component, incidents)
    
    if not impacts:
        st.warning("No downstream components found. This change appears isolated.")
    else:
        # Gather evidence
        evidence_map = {}
        for imp in impacts:
            evidence_map[imp["component"]] = get_evidence(collection, imp["component"], field)
        
        with st.spinner("Reasoning with AI agent..."):
            report = analyze_with_llm(change, impacts, evidence_map)
        
        # Overall recommendation
        st.success(f"### 📋 Overall Recommendation\n{report['overall_recommendation']}")
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        high = sum(1 for i in report["impacts"] if i["risk"] == "High")
        med = sum(1 for i in report["impacts"] if i["risk"] == "Medium")
        low = sum(1 for i in report["impacts"] if i["risk"] == "Low")
        col1.metric("🔴 High Risk", high)
        col2.metric("🟡 Medium Risk", med)
        col3.metric("🟢 Low Risk", low)

        st.divider()
        st.subheader("AI Impact Tree")
        impacted_names = [item["component"] for item in report["impacts"]]
        graph_fig = build_impact_tree(G, component, impacted_names)
        if graph_fig is not None:
            st.pyplot(graph_fig)
            st.caption("AI agent mode: LLM reasoning enabled" if ai_agent_enabled and ai_available else "AI agent mode: fallback reasoning")

        st.divider()
        st.subheader("Impacted Components")
        
        # Sort: High -> Medium -> Low
        order = {"High": 0, "Medium": 1, "Low": 2}
        sorted_impacts = sorted(report["impacts"], key=lambda x: order[x["risk"]])
        
        for imp in sorted_impacts:
            emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}[imp["risk"]]
            with st.expander(f"{emoji} **{imp['component']}** — {imp['risk']} Risk"):
                st.write(f"**Why affected:** {imp['reasoning']}")
                st.write(f"**What could go wrong:** {imp['failure_mode']}")
                st.write("**Evidence:**")
                for e in imp["evidence"]:
                    st.write(f"- {e}")
                st.write(f"**Recommendation:** {imp['recommendation']}")
        
        # Show dependency graph
        st.divider()
        st.subheader("Dependency Path Visualization")
        for imp in sorted_impacts[:5]:
            st.code(imp.get("reasoning", "")[:200])
else:
    st.info("👈 Configure a change in the sidebar and click **Analyze Impact**.")