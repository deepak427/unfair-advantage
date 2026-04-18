"""
Graphiti → Neo4j ingestor.
Takes chunks and builds a temporal knowledge graph of concepts and relationships.
"""
import asyncio
from datetime import datetime, timezone
from loguru import logger
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from config.settings import settings
from ingestion.pdf_extractor import Chunk

_graphiti: Graphiti | None = None


def _get_graphiti() -> Graphiti:
    global _graphiti
    if _graphiti is None:
        _graphiti = Graphiti(
            uri=settings.neo4j_uri,
            user=settings.neo4j_username,
            password=settings.neo4j_password,
            llm_client=GeminiClient(model=settings.gemini_model_ingestion),
            embedder=GeminiEmbedder(
                config=GeminiEmbedderConfig(embedding_model="models/text-embedding-004")
            ),
        )
    return _graphiti


async def ingest_chunks_to_graph(chunks: list[Chunk]) -> dict:
    """Send chunks to Graphiti which extracts entities/relationships into Neo4j."""
    graphiti = _get_graphiti()
    await graphiti.build_indices_and_constraints()

    episodes_created = 0
    errors = []

    for chunk in chunks:
        try:
            episode_id = f"{chunk.source_file}__chunk_{chunk.chunk_index}"
            await graphiti.add_episode(
                name=episode_id,
                episode_body=chunk.text,
                source_description=f"Book: {chunk.book_title} | File: {chunk.source_file}",
                reference_time=datetime.now(timezone.utc),
                group_id=chunk.source_file,  # groups all chunks from same book
            )
            episodes_created += 1
            logger.debug(f"Graph episode added: {episode_id}")

            # small delay to avoid overwhelming the LLM API
            await asyncio.sleep(0.3)

        except Exception as e:
            error_msg = f"Failed chunk {chunk.chunk_index}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    logger.info(f"Graph ingestion done: {episodes_created} episodes, {len(errors)} errors")
    return {"episodes_created": episodes_created, "errors": errors}


async def close_graph():
    global _graphiti
    if _graphiti:
        await _graphiti.close()
        _graphiti = None
