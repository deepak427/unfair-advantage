"""
Main ingestion pipeline.
Usage:
    python -m ingestion.pipeline --file books/atomic_habits.pdf
    python -m ingestion.pipeline --all          # process all unprocessed books in GCS
"""
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from loguru import logger

from ingestion.gcs_client import upload_book, is_processed, mark_processed, list_unprocessed_books
from ingestion.pdf_extractor import extract_chunks
from ingestion.rag_ingestor import ingest_gcs_file
from ingestion.graph_ingestor import ingest_chunks_to_graph, close_graph


async def ingest_book(pdf_path: str | Path) -> dict:
    """Full pipeline for a single PDF: GCS → RAG Engine + Neo4j."""
    pdf_path = Path(pdf_path)

    if is_processed(pdf_path.name):
        logger.info(f"Already processed: {pdf_path.name} — skipping")
        return {"skipped": True, "file": pdf_path.name}

    start = datetime.now()
    logger.info(f"Starting ingestion: {pdf_path.name}")

    # 1. Upload to GCS
    gcs_uri = upload_book(pdf_path)

    # 2. Vertex AI RAG Engine (handles embedding internally)
    ingest_gcs_file(gcs_uri)

    # 3. Extract chunks locally for Graphiti
    chunks = extract_chunks(pdf_path)

    # 4. Build knowledge graph (skip if SKIP_GRAPH_BUILDING=true)
    import os
    if os.getenv("SKIP_GRAPH_BUILDING", "false").lower() == "true":
        logger.info("Skipping graph building (SKIP_GRAPH_BUILDING=true)")
        graph_result = {"episodes_created": 0, "errors": []}
    else:
        graph_result = await ingest_chunks_to_graph(chunks)

    elapsed = (datetime.now() - start).total_seconds()

    result = {
        "file": pdf_path.name,
        "gcs_uri": gcs_uri,
        "chunks": len(chunks),
        "graph_episodes": graph_result["episodes_created"],
        "graph_errors": len(graph_result["errors"]),
        "elapsed_seconds": round(elapsed, 1),
    }

    mark_processed(pdf_path.name, result)
    logger.info(f"Done: {pdf_path.name} in {elapsed:.1f}s")
    return result


async def ingest_all_pending() -> list[dict]:
    """Process all books in GCS that haven't been ingested yet."""
    pending = list_unprocessed_books()
    if not pending:
        logger.info("No unprocessed books found in GCS")
        return []

    logger.info(f"Found {len(pending)} unprocessed books")
    results = []
    for gcs_uri in pending:
        # download not needed — RAG ingestor reads from GCS directly
        # but graph ingestor needs local file, so we note this limitation
        logger.warning(f"--all mode requires local files. Use --file for: {gcs_uri}")
    return results


async def main():
    parser = argparse.ArgumentParser(description="Ingest books into RAG + Knowledge Graph")
    parser.add_argument("--file", "-f", help="Path to a local PDF file")
    parser.add_argument("--all", "-a", action="store_true", help="Process all unprocessed books in GCS")
    args = parser.parse_args()

    try:
        if args.file:
            result = await ingest_book(args.file)
            print(f"\nResult: {result}")
        elif args.all:
            results = await ingest_all_pending()
            print(f"\nProcessed {len(results)} books")
        else:
            parser.print_help()
    finally:
        await close_graph()


if __name__ == "__main__":
    asyncio.run(main())
