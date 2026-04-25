"""
Graphiti → Neo4j knowledge graph ingestor.
Uses Gemini API (free tier) for entity extraction and embeddings.
"""
import asyncio
import re
from datetime import datetime, timezone
from loguru import logger
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.llm_client import LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.client import CrossEncoderClient
from config.settings import settings
from ingestion.pdf_extractor import Chunk


class NoOpCrossEncoder(CrossEncoderClient):
    """Skips OpenAI reranker — not needed for our use case."""
    async def rank(self, query: str, passages: list[str]) -> list[float]:
        return [1.0] * len(passages)


_graphiti: Graphiti | None = None


def _get_graphiti() -> Graphiti:
    from graphiti_core.driver.neo4j_driver import Neo4jDriver
    global _graphiti
    if _graphiti is None:
        # Create driver with high stability settings for long LLM calls
        driver = Neo4jDriver(
            uri=settings.neo4j_uri,
            user=settings.neo4j_username,
            password=settings.neo4j_password,
            database=None
        )
        
        # Manually tune the underlying Neo4j client for reliability
        from neo4j import AsyncGraphDatabase
        driver.client = AsyncGraphDatabase.driver(
            uri=settings.neo4j_uri,
            auth=(settings.neo4j_username or '', settings.neo4j_password or ''),
            keep_alive=True,
            max_connection_lifetime=3600
        )
        
        _graphiti = Graphiti(
            graph_driver=driver,
            llm_client=GeminiClient(
                config=LLMConfig(
                    model=settings.gemini_model_ingestion,
                    api_key=settings.gemini_api_key,
                )
            ),
            embedder=GeminiEmbedder(
                config=GeminiEmbedderConfig(
                    embedding_model="gemini-embedding-001",
                    embedding_dim=1536,
                    api_key=settings.gemini_api_key,
                )
            ),
            cross_encoder=NoOpCrossEncoder(),
            max_coroutines=1  # Sequential processing for free tier stability
        )
    return _graphiti


def _safe_group_id(filename: str) -> str:
    """Graphiti group_id only allows alphanumeric, dashes, underscores."""
    return re.sub(r"[^a-zA-Z0-9_-]", "-", filename)


async def ingest_chunks_to_graph(chunks: list[Chunk]) -> dict:
    """
    Send chunks to Graphiti which extracts entities/relationships into Neo4j.
    Each chunk = 1 LLM call (entity extraction) + 1 embedding call.
    """
    graphiti = _get_graphiti()
    await graphiti.build_indices_and_constraints()

    episodes_created = 0
    errors = []
    group_id = _safe_group_id(chunks[0].source_file if chunks else "unknown")

    for chunk in chunks:
        try:
            episode_id = f"{group_id}__chunk_{chunk.chunk_index}"
            
            # Check if this chunk was already processed (Resume Support)
            query = "MATCH (e:Episodic {name: $name}) RETURN e.uuid LIMIT 1"
            async with graphiti.driver.client.session() as session:
                result = await session.run(query, name=episode_id)
                record = await result.single()
                if record:
                    print(f"  ✔  [SKIPPING] Chunk {chunk.chunk_index + 1} already in graph.")
                    episodes_created += 1
                    continue

            print(f"  ℹ  [STARTING] Processing chunk {episodes_created + 1}/{len(chunks)}...")
            
            # Clean text of junk characters that cause LLM hallucinations
            clean_text = re.sub(r'[\r\t\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', ' ', chunk.text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            await graphiti.add_episode(
                name=episode_id,
                episode_body=clean_text,
                source_description=f"Book: {chunk.book_title}",
                reference_time=datetime.now(timezone.utc),
                group_id=group_id,
            )
            episodes_created += 1
            logger.info(f"Graph episode {episodes_created}/{len(chunks)} successful: {episode_id}")
            await asyncio.sleep(0.5)

        except Exception as e:
            error_msg = f"Chunk {chunk.chunk_index}: {e}"
            print(f"  ✗  [FAILED] Chunk {chunk.chunk_index + 1}: {e}")
            logger.error(error_msg)
            errors.append(error_msg)

    logger.info(f"Graph done: {episodes_created} episodes, {len(errors)} errors")
    return {"episodes_created": episodes_created, "errors": errors}


async def close_graph():
    global _graphiti
    if _graphiti:
        await _graphiti.close()
        _graphiti = None
