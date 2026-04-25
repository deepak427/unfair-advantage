"""
Graph search tool — queries Neo4j via Graphiti.
Finds relationships, concepts, and connections across books.
"""
from loguru import logger
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.llm_client import LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from config.settings import settings


class NoOpCrossEncoder(CrossEncoderClient):
    """Passthrough reranker — skips OpenAI dependency."""
    async def rank(self, query: str, passages: list[str]) -> list[float]:
        return [1.0] * len(passages)


_graphiti: Graphiti | None = None


def _get_graphiti() -> Graphiti:
    global _graphiti
    if _graphiti is None:
        # Create driver with high stability settings for long calls
        # Use database=None to auto-select current database (AuraDB fix)
        driver = Neo4jDriver(
            uri=settings.neo4j_uri,
            user=settings.neo4j_username,
            password=settings.neo4j_password,
            database=None
        )
        
        _graphiti = Graphiti(
            graph_driver=driver,
            llm_client=GeminiClient(
                config=LLMConfig(
                    model=settings.gemini_model_root,
                    api_key=settings.gemini_api_key
                )
            ),
            embedder=GeminiEmbedder(
                config=GeminiEmbedderConfig(
                    embedding_model="gemini-embedding-001",
                    embedding_dim=1536,
                    api_key=settings.gemini_api_key
                )
            ),
            cross_encoder=NoOpCrossEncoder(),
        )
    return _graphiti


async def search_graph(query: str, top_k: int = None) -> str:
    """
    Search the knowledge graph for concepts, relationships, and connections.

    Use this tool when you need to understand how concepts relate to each other,
    find connections across different books, or explore how ideas evolved.
    Best for questions like "how does X relate to Y?" or "what books discuss Z?".

    Args:
        query: Concept or relationship to search for.
               Example: "identity change habits" or "deep work flow state"
        top_k: Number of graph facts to return

    Returns:
        Formatted string with facts and relationships found in the knowledge graph.
    """
    limit = top_k or settings.max_graph_results

    try:
        graphiti = _get_graphiti()

        results = await graphiti.search(query, num_results=limit)

        if not results:
            return f"No graph relationships found for: '{query}'"

        facts = []
        for i, edge in enumerate(results, 1):
            fact = getattr(edge, "fact", None) or str(edge)
            facts.append(f"[{i}] {fact}")

        return "\n".join(facts)

    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        return f"Graph search error: {str(e)}"
