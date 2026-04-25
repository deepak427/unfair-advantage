"""
Interactive book ingestion — walks through every step with explanations.
Usage: python ingest.py books/your_book.pdf
       python ingest.py books/your_book.pdf --skip-graph
"""
import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime


def header(n, title, why):
    print(f"\n{'='*60}")
    print(f"  STEP {n}: {title}")
    print(f"  WHY: {why}")
    print(f"{'='*60}")

def ok(msg):   print(f"  ✓  {msg}")
def fail(msg): print(f"  ✗  {msg}")
def info(msg): print(f"  ℹ  {msg}")
def warn(msg): print(f"  ⚠  {msg}")

def pause():
    import time
    time.sleep(0.1)
    try:
        input("\n  ▶  Press Enter to continue...")
    except EOFError:
        print("\n  ℹ  (Automatic continue - terminal input restricted)")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to PDF, e.g. books/gita.pdf")
    parser.add_argument("--skip-graph", action="store_true", default=False,
                        help="Skip Neo4j graph building (faster, RAG still works)")
    args = parser.parse_args()
    pdf_path = Path(args.file)

    print(f"\n{'='*60}")
    print(f"  UNFAIR ADVANTAGE — Book Ingestion")
    print(f"  File : {pdf_path.name}")
    print(f"  Time : {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    info("Each step will explain what it does and why.")
    info("Press Enter after each step to continue.")
    pause()

    # ── Step 1: Settings ──────────────────────────────────────
    header(1, "Load configuration",
           "Reads all values from .env. Every other step depends on these.")
    try:
        from config.settings import settings
        ok(f"Gemini model    : {settings.gemini_model_root}")
        ok(f"Embedding model : {settings.embedding_model}")
        ok(f"Database        : {settings.database_url[:40]}...")
        ok(f"Neo4j           : {settings.neo4j_uri[:40]}...")
        ok(f"Chunk size      : {settings.chunk_size} chars, overlap {settings.chunk_overlap}")
    except Exception as e:
        fail(f"Settings error: {e}")
        info("Check your .env file — all required keys must be filled in")
        sys.exit(1)
    pause()

    # ── Step 2: Validate PDF ──────────────────────────────────
    header(2, "Validate PDF file",
           "Checks the file exists before doing anything expensive.")
    if not pdf_path.exists():
        fail(f"File not found: {pdf_path}")
        info("Put the PDF in the books/ folder and try again.")
        sys.exit(1)
    size_mb = pdf_path.stat().st_size / 1024 / 1024
    ok(f"Found: {pdf_path.name} ({size_mb:.1f} MB)")
    pause()

    # ── Step 3: Database schema ───────────────────────────────
    header(3, "Set up Postgres schema",
           "Creates the 'books' and 'chunks' tables in Neon if they don't exist. "
           "The chunks table has a 'vector(1536)' column for storing embeddings. "
           "Also creates an ivfflat index for fast similarity search. "
           "Safe to run multiple times — uses IF NOT EXISTS.")
    try:
        from ingestion.db_ingestor import setup_schema
        info("Connecting to Neon Postgres...")
        await setup_schema()
        ok("Schema ready (tables + indexes exist)")
    except Exception as e:
        fail(f"Database setup failed: {e}")
        info("Check DATABASE_URL in .env — must be a valid Neon connection string")
        info("Get it from: https://console.neon.tech → your project → Connection string")
        sys.exit(1)
    pause()

    # ── Step 4: Check if already ingested ────────────────────
    header(4, "Check if book already ingested",
           "Looks for an existing record in the 'books' table. "
           "Avoids re-ingesting the same book and wasting API quota.")
    skip_postgres = False
    try:
        from ingestion.db_ingestor import book_exists, delete_book
        exists = await book_exists(pdf_path.name)
        if exists:
            warn(f"'{pdf_path.name}' is already in the database.")
            answer = input("  ▶  Re-ingest and overwrite? (y/n): ").strip().lower()
            if answer != "y":
                info("Skipping Postgres records. Proceeding to Knowledge Graph check...")
                skip_postgres = True
            else:
                await delete_book(pdf_path.name)
                ok("Deleted existing data — will re-ingest fresh")
        else:
            ok("Not yet ingested — proceeding")
    except Exception as e:
        warn(f"Could not check: {e} — continuing anyway")
    pause()

    # ── Step 5: Extract chunks ────────────────────────────────
    header(5, "Extract text chunks from PDF",
           "Uses PyMuPDF to read the PDF and split text into overlapping chunks. "
           f"Each chunk is ~{settings.chunk_size} characters with {settings.chunk_overlap} char overlap. "
           "Overlap ensures context isn't lost at chunk boundaries. "
           "Example: a 200-page book becomes ~300 chunks.")
    try:
        from ingestion.pdf_extractor import extract_chunks
        info(f"Reading {pdf_path.name} with PyMuPDF...")
        chunks = extract_chunks(pdf_path)
        ok(f"Extracted {len(chunks)} chunks")
        ok(f"Book title detected: '{chunks[0].book_title}'")
        info(f"First chunk preview: {chunks[0].text[:120].strip()}...")
    except Exception as e:
        fail(f"PDF extraction failed: {e}")
        info("Is the PDF readable? Try opening it manually to verify.")
        sys.exit(1)
    
    if not skip_postgres:
        pause()

        header(6, "Generate embeddings with Gemini",
            "Converts each chunk of text into a list of numbers (a vector). "
            "Similar meanings → similar vectors. This is what enables semantic search. "
            "Example: 'warrior duty' and 'Arjuna obligation' will have similar vectors "
            "even though the words are different. "
            f"Will make ~{len(chunks)//100 + 1} API calls (batches of 100). "
            "Free tier: 1500 requests/day.")
        try:
            from ingestion.embedder import embed_texts
            info(f"Embedding {len(chunks)} chunks via Gemini API...")
            info("This may take 1-2 minutes...")
            texts = [c.text for c in chunks]
            embeddings = await embed_texts(texts)
            ok(f"Generated {len(embeddings)} embeddings")
            ok(f"Each embedding: {len(embeddings[0])} dimensions")
        except Exception as e:
            fail(f"Embedding failed: {e}")
            info("Check GEMINI_API_KEY in .env")
            info("Get a free key at: https://aistudio.google.com/apikey")
            sys.exit(1)
        pause()

        # ── Step 7: Save to Postgres ──────────────────────────────
        header(7, "Save chunks + embeddings to Neon Postgres",
            "Stores all chunks and their embedding vectors in the database. "
            "After this step, the book is fully searchable by meaning. "
            "The ivfflat index makes similarity search fast even with millions of chunks.")
        try:
            from ingestion.db_ingestor import save_book_and_chunks
            info(f"Saving {len(chunks)} chunks to Postgres...")
            
            # Combine chunks and embeddings
            for i, emb in enumerate(embeddings):
                chunks[i].embedding = emb
            
            success = await save_book_and_chunks(chunks)
            if success:
                ok("Postgres ingestion complete")
            else:
                fail("Database save failed")
                sys.exit(1)
        except Exception as e:
            fail(f"Database save failed: {e}")
            info("Check DATABASE_URL in .env")
            sys.exit(1)
        pause()
    else:
        info("Skipping STEP 6 & 7 (Postgres already has this book).")

    # ── Step 8: Knowledge graph ───────────────────────────────
    skip_graph = args.skip_graph or os.getenv("SKIP_GRAPH_BUILDING", "false").lower() == "true"

    header(8, "Build knowledge graph in Neo4j via Graphiti",
           "For each chunk, Gemini reads the text and extracts entities "
           "(people, concepts, places) and relationships between them. "
           "Stored as nodes/edges in Neo4j. "
           "Enables questions like 'how does dharma connect to Arjuna?' "
           "that pure vector search cannot answer. "
           f"Will make ~{len(chunks)} LLM calls. Free tier: 1500/day. "
           "Estimated time: ~10-20 minutes for 300 chunks.")
    if skip_graph:
        warn("SKIPPING graph building (--skip-graph flag set)")
        info("RAG search still works perfectly without the graph.")
        info("Run again without --skip-graph to build the graph later.")
        graph_result = {"episodes_created": 0, "errors": []}
    else:
        try:
            from ingestion.graph_ingestor import ingest_chunks_to_graph, close_graph
            info(f"Processing {len(chunks)} chunks through Graphiti...")
            info("You'll see progress as each episode is added...")
            graph_result = await ingest_chunks_to_graph(chunks)
            ok(f"Graph episodes created: {graph_result['episodes_created']}")
            if graph_result["errors"]:
                warn(f"{len(graph_result['errors'])} chunks failed in graph")
            await close_graph()
        except Exception as e:
            fail(f"Graph building failed: {e}")
            info("RAG search still works — graph is optional")
            graph_result = {"episodes_created": 0, "errors": [str(e)]}
    pause()

    # ── Done ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  INGESTION COMPLETE")
    print(f"{'='*60}")
    ok(f"Book       : {pdf_path.name}")
    ok(f"Chunks     : {len(chunks)} stored in Postgres")
    ok(f"Graph      : {graph_result['episodes_created']} episodes in Neo4j")
    print()
    print("  Next: start the agent")
    print("  python -m agent.agent  (or via ADK)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
