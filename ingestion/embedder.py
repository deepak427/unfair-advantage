"""
Embedding generation using Gemini API.
Free tier: 1500 requests/day.
"""
import asyncio
from typing import List
import google.generativeai as genai
from loguru import logger
from config.settings import settings

# Configure Gemini API key once
genai.configure(api_key=settings.gemini_api_key)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Processes in batches of 100 (API limit) with small delays to stay under quota.
    """
    all_embeddings = []
    batch_size = 100

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            result = genai.embed_content(
                model=f"models/{settings.embedding_model}",
                content=batch,
                task_type="retrieval_document",
                output_dimensionality=1536,
            )
            all_embeddings.extend(result["embedding"])
        except Exception as e:
            logger.error(f"Embedding batch {i//batch_size + 1} failed: {e}")
            raise

        if i + batch_size < len(texts):
            await asyncio.sleep(0.5)

    return all_embeddings


async def embed_query(query: str) -> List[float]:
    """Generate embedding for a search query."""
    try:
        result = genai.embed_content(
            model=f"models/{settings.embedding_model}",
            content=query,
            task_type="retrieval_query",
            output_dimensionality=1536,
        )
        return result["embedding"]
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        raise
