# Change Impact Analyzer

A Streamlit app for predicting engineering change impact using a dependency graph, historical incident evidence, and AI-assisted reasoning.

## Features

- Select a component and propose a config change
- Compute downstream impact using graph traversal
- Score risk based on dependency hops, edge criticality, component criticality, and historical incidents
- Retrieve similar historical incidents from a ChromaDB evidence store
- Produce a human-readable impact report using AI or a deterministic fallback

## Run locally

1. Create and activate a virtual environment
   - Windows PowerShell:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
2. Install dependencies
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Start the app
   ```powershell
   streamlit run app.py
   ```

## Optional AI configuration

The app falls back to a built-in analysis if no API key is supplied. If you want AI-generated reasoning, set one of these environment variables before launching:

```powershell
$env:OLLAMA_API_KEY="your-key"
# or
$env:OPENAI_API_KEY="your-key"
```

## Project structure

- [app.py](app.py): Streamlit UI entry point
- [src/graph_loader.py](src/graph_loader.py): Graph data loader
- [src/impact_engine.py](src/impact_engine.py): Impact analysis and risk scoring
- [src/evidence_retriever.py](src/evidence_retriever.py): Incident retrieval from ChromaDB
- [src/llm_reasoner.py](src/llm_reasoner.py): AI or fallback analysis
- [data/system_graph.json](data/system_graph.json): Dependency graph data
- [data/incidents.json](data/incidents.json): Historical incident records
