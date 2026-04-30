"""
RAG search tool — queries Neon Postgres via pgvector.
Returns top matching chunks with book title and source info.
"""
from loguru import logger
from config.settings import settings
from ingestion.db_ingestor import vector_search
from ingestion.embedder import embed_query

async def search_rag(query: str, book_filename: str = None, top_k: int = None) -> str:
    """
    Search the book knowledge base using semantic similarity.

    Use this tool when you need to find relevant passages, explanations,
    or information from the ingested books. Returns the most relevant
    text chunks with their source book and location.

    Args:
        query: The search query — be specific for better results.
               Example: "habit loop cue routine reward"
        book_filename: Context filter. Pass the original filename to restrict search.
                       Example: "Gitapress_Gita_Roman.pdf" or "kojiki.pdf"
        top_k: Number of results to return

    Returns:
        Formatted string with matching passages and their sources.
    """
    limit = top_k or settings.max_rag_results

    try:
        # 1. Generate embedding for the query
        query_embedding = await embed_query(query)

        # 2. Search Postgres
        hits = await vector_search(query_embedding, limit=limit, source_file=book_filename)

        if not hits:
            return f"No results found for query: '{query}'"

        results = []
        for i, hit in enumerate(hits, 1):
            book_title = hit.get("book_title", "Unknown Book")
            similarity = round(hit.get("similarity", 0), 3)
            content = hit.get("content", "").strip()

            results.append(
                f"[{i}] Source: {book_title} (similarity: {similarity})\n"
                f"{content}\n"
            )

        return "\n---\n".join(results)

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return f"RAG search error: {str(e)}"
