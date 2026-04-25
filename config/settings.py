"""
Central settings — loaded once, imported everywhere.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Force .env to override any system-level environment variables
load_dotenv(override=True)


class Settings(BaseSettings):
    # ── Gemini API ────────────────────────────────────────────
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model_root: str = Field("gemini-2.0-flash", alias="GEMINI_MODEL_ROOT")
    gemini_model_reasoning: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL_REASONING")
    gemini_model_ingestion: str = Field("gemini-2.0-flash", alias="GEMINI_MODEL_INGESTION")
    embedding_model: str = Field("gemini-embedding-001", alias="EMBEDDING_MODEL")

    # ── Neon Postgres (vector store) ──────────────────────────
    database_url: str = Field(..., alias="DATABASE_URL")

    # ── Neo4j / Graphiti ──────────────────────────────────────
    neo4j_uri: str = Field(..., alias="NEO4J_URI")
    neo4j_username: str = Field(..., alias="NEO4J_USERNAME")
    neo4j_password: str = Field(..., alias="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", alias="NEO4J_DATABASE")

    # ── Ingestion ─────────────────────────────────────────────
    chunk_size: int = Field(1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(200, alias="CHUNK_OVERLAP")

    # ── Agent ─────────────────────────────────────────────────
    max_rag_results: int = Field(10, alias="MAX_RAG_RESULTS")
    max_graph_results: int = Field(10, alias="MAX_GRAPH_RESULTS")
    app_port: int = Field(8080, alias="APP_PORT")
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = Settings()
