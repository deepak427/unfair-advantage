"""
Vertex AI RAG Engine ingestor.
Creates the corpus once, then imports chunks as RAG files.
Auth: gcloud ADC — no API key needed.
"""
import vertexai
from vertexai.preview import rag
from loguru import logger
from config.settings import settings

_corpus: rag.RagCorpus | None = None


def _init_vertexai():
    vertexai.init(project=settings.gcp_project_id, location=settings.vertex_ai_location)


def get_or_create_corpus() -> rag.RagCorpus:
    """Get existing corpus by display name or create a new one."""
    global _corpus
    if _corpus:
        return _corpus

    _init_vertexai()

    # Check if corpus already exists
    for corpus in rag.list_corpora():
        if corpus.display_name == settings.vertex_ai_rag_corpus_name:
            logger.info(f"Using existing RAG corpus: {corpus.display_name}")
            _corpus = corpus
            return _corpus

    # Create corpus explicitly with RagManagedDb backend (serverless)
    # Using embedding_model_config alone triggers the old Vertex Vector Search backend
    # which requires allowlisting. RagManagedDb is the serverless backend — no allowlist needed.
    logger.info(f"Creating RAG corpus (serverless backend): {settings.vertex_ai_rag_corpus_name}")
    _corpus = rag.create_corpus(
        display_name=settings.vertex_ai_rag_corpus_name,
        embedding_model_config=rag.EmbeddingModelConfig(
            publisher_model=f"publishers/google/models/{settings.vertex_ai_embedding_model}"
        ),
    )
    logger.info(f"Created corpus: {_corpus.name}")

    return _corpus


def ingest_gcs_file(gcs_uri: str) -> None:
    """
    Import a PDF directly from GCS into the RAG corpus.
    Vertex AI handles chunking + embedding automatically for GCS imports.
    """
    corpus = get_or_create_corpus()
    logger.info(f"Importing {gcs_uri} into RAG corpus...")

    rag.import_files(
        corpus_name=corpus.name,
        paths=[gcs_uri],
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    logger.info(f"Import complete: {gcs_uri}")


def get_corpus_name() -> str:
    """Return the full resource name of the corpus (needed for search)."""
    return get_or_create_corpus().name
