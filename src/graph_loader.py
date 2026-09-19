import json
import networkx as nx
import os

def load_graph(path="data/system_graph.json"):
    with open(path) as f:
        data = json.load(f)
    
    G = nx.DiGraph()
    for node in data["nodes"]:
        G.add_node(node["id"], **node)
    for edge in data["edges"]:
        G.add_edge(edge["from"], edge["to"], **edge)
    
    return G

if __name__ == "__main__":
    G = load_graph()
    print(f"Loaded {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    print("Sample node:", list(G.nodes)[0])
