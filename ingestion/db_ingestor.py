"""
Postgres + pgvector ingestor.
Stores book chunks and their embeddings in Neon Postgres.
"""
import json
import asyncpg
from loguru import logger
from config.settings import settings
from ingestion.pdf_extractor import Chunk

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def setup_schema():
    """
    Create tables and indexes if they don't exist.
    Uses pgvector for semantic search + tsvector for keyword search.
    Dimension 1536 matches standard AI model output and fits in Postgres indexes.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                source_file TEXT NOT NULL UNIQUE,
                ingested_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY,
                book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                book_title TEXT NOT NULL,
                source_file TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1536),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Vector similarity index
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding
            ON chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10)
        """)

        # Full-text search index
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_content_fts
            ON chunks USING GIN (to_tsvector('english', content))
        """)

    logger.info("Database schema ready")


async def book_exists(source_file: str) -> bool:
    """Check if a book has already been ingested."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM books WHERE source_file = $1", source_file
        )
        return row is not None


async def delete_book(source_file: str):
    """Delete all chunks for a book (for re-ingestion)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM books WHERE source_file = $1", source_file)
    logger.info(f"Deleted existing data for {source_file}")


async def save_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    """
    Save chunks and their embeddings to Postgres.
    Returns the number of chunks saved.
    """
    if not chunks:
        return 0

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Insert book record
            book_id = await conn.fetchval(
                """
                INSERT INTO books (title, source_file)
                VALUES ($1, $2)
                ON CONFLICT (source_file) DO UPDATE SET title = EXCLUDED.title
                RETURNING id
                """,
                chunks[0].book_title,
                chunks[0].source_file,
            )

            # Insert all chunks
            for chunk, embedding in zip(chunks, embeddings):
                vec_str = "[" + ",".join(map(str, embedding)) + "]"
                await conn.execute(
                    """
                    INSERT INTO chunks
                        (book_id, book_title, source_file, chunk_index, content, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6::vector)
                    """,
                    book_id,
                    chunk.book_title,
                    chunk.source_file,
                    chunk.chunk_index,
                    chunk.text,
                    vec_str,
                )

    logger.info(f"Saved {len(chunks)} chunks to Postgres")
    return len(chunks)


async def vector_search(query_embedding: list[float], limit: int = 10) -> list[dict]:
    """Find the most semantically similar chunks to a query."""
    pool = await get_pool()
    vec_str = "[" + ",".join(map(str, query_embedding)) + "]"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id, book_title, source_file, chunk_index, content,
                1 - (embedding <=> $1::vector) AS similarity
            FROM chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            vec_str, limit
        )
    return [dict(r) for r in rows]
