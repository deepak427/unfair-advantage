# Unfair Advantage — Agentic RAG Knowledge System

A hybrid RAG + Knowledge Graph system for deep book knowledge.
Built with Google ADK, Neon Postgres, pgvector, Neo4j, and Graphiti.

## Stack
- **Agent**: Google ADK + Gemini 2.5
- **Vector Store**: Neon Postgres + pgvector (gemini-embedding-001)
- **Knowledge Graph**: Neo4j AuraDB + Graphiti
- **PDF Processing**: PyMuPDF

## Project Structure
```
unfair-advantage/
├── config/
│   └── settings.py          # All env vars, typed via pydantic-settings
├── ingestion/
│   ├── pdf_extractor.py     # PDF → text chunks
│   ├── db_ingestor.py       # Chunks → Neon Postgres (pgvector)
│   ├── embedder.py          # Gemini Embeddings
│   └── graph_ingestor.py    # Chunks → Graphiti → Neo4j
├── agent/
│   ├── tools/
│   │   ├── rag_search.py    # Neon Postgres RAG search tool
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

# Setup Database & Secrets
cp .env.example .env
# Fill out your .env variables (Neon Postgres, Gemini, Neo4j)
```

## Usage
```bash
# 1. Add PDFs to books/ folder

# 2. Run ingestion
python ingest.py books/your_book.pdf

# 3. Start agent
adk run agent
```
