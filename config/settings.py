"""
Central settings — loaded once, imported everywhere.
Uses pydantic-settings so every value is typed and validated on startup.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ── Google Cloud ──────────────────────────────────────────
    gcp_project_id: str = Field(..., alias="GCP_PROJECT_ID")
    gcp_region: str = Field("us-central1", alias="GCP_REGION")
    gcs_bucket_name: str = Field(..., alias="GCS_BUCKET_NAME")

    # ── Vertex AI ─────────────────────────────────────────────
    vertex_ai_rag_corpus_name: str = Field("books-rag-corpus", alias="VERTEX_AI_RAG_CORPUS_NAME")
    vertex_ai_embedding_model: str = Field("text-embedding-004", alias="VERTEX_AI_EMBEDDING_MODEL")
    vertex_ai_location: str = Field("us-central1", alias="VERTEX_AI_LOCATION")

    # ── Gemini Models ─────────────────────────────────────────
    gemini_model_root: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL_ROOT")
    gemini_model_reasoning: str = Field("gemini-2.5-pro", alias="GEMINI_MODEL_REASONING")
    gemini_model_ingestion: str = Field("gemini-2.0-flash", alias="GEMINI_MODEL_INGESTION")

    # ── Neo4j / Graphiti ──────────────────────────────────────
    neo4j_uri: str = Field(..., alias="NEO4J_URI")
    neo4j_username: str = Field(..., alias="NEO4J_USERNAME")
    neo4j_password: str = Field(..., alias="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", alias="NEO4J_DATABASE")

    # ── Ingestion ─────────────────────────────────────────────
    chunk_size: int = Field(1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(200, alias="CHUNK_OVERLAP")
    max_chunks_per_batch: int = Field(50, alias="MAX_CHUNKS_PER_BATCH")

    # ── Agent ─────────────────────────────────────────────────
    max_rag_results: int = Field(10, alias="MAX_RAG_RESULTS")
    max_graph_results: int = Field(10, alias="MAX_GRAPH_RESULTS")
    app_port: int = Field(8080, alias="APP_PORT")
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "populate_by_name": True}


# Single instance — import this everywhere
settings = Settings()
