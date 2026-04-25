# Unfair Advantage — Agentic RAG Knowledge System

A hybrid RAG + Knowledge Graph system for deep book knowledge.
Built with Google ADK, Vertex AI RAG Engine, Neo4j, and Graphiti.

## Stack
- **Agent**: Google ADK + Gemini 2.5
- **Vector Store**: Neon Postgres + pgvector (gemini-embedding-001)
- **Knowledge Graph**: Neo4j AuraDB + Graphiti
- **File Storage**: Google Cloud Storage
- **PDF Processing**: PyMuPDF

## Project Structure
```
unfair-advantage/
├── config/
│   └── settings.py          # All env vars, typed via pydantic-settings
├── ingestion/
│   ├── pdf_extractor.py     # PDF → text chunks
│   ├── gcs_client.py        # Upload/download from GCS
│   ├── rag_ingestor.py      # Chunks → Vertex AI RAG Engine
│   ├── graph_ingestor.py    # Chunks → Graphiti → Neo4j
│   └── pipeline.py          # Orchestrates full ingestion
├── agent/
│   ├── tools/
│   │   ├── rag_search.py    # Vertex AI RAG search tool
│   │   └── graph_search.py  # Neo4j graph search tool
│   ├── sub_agents/          # Specialized sub-agents
│   ├── prompt.py            # System prompts
│   └── agent.py             # Root ADK agent
├── books/                   # Local PDFs (gitignored)
├── .env                     # Your secrets (gitignored)
├── .env.example             # Template
└── requirements.txt
```

## Setup
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Auth (already done)
gcloud auth application-default login
gcloud config set project unfair-advantage-6
```

## Usage
```bash
# 1. Add PDFs to books/ folder

# 2. Run ingestion
python -m ingestion.pipeline --file books/your_book.pdf

# 3. Start agent
adk run agent
```
