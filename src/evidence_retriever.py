import json
import chromadb

def init_incident_store(path="data/incidents.json"):
    with open(path) as f:
        incidents = json.load(f)
    
    client = chromadb.Client()
    # Delete if exists (for re-runs)
    try:
        client.delete_collection("incidents")
    except:
        pass
    
    collection = client.create_collection("incidents")
    
    for inc in incidents:
        text = f"{inc['title']}. Root cause: {inc['root_cause']}. Change: {inc['change_that_triggered']}"
        collection.add(
            documents=[text],
            metadatas=[{
                "id": inc["id"],
                "title": inc["title"],
                "root_cause": inc["root_cause"],
                "change": inc["change_that_triggered"],
                "severity": inc["severity"],
                "resolution": inc["resolution"]
            }],
            ids=[inc["id"]]
        )
    
    return collection, incidents

def get_evidence(collection, component, field, n=3):
    query = f"{component} affected by change to {field}"
    results = collection.query(query_texts=[query], n_results=n)
    return results["metadatas"][0] if results["metadatas"] else []
