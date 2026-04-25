"""
Unfair Advantage — Step-by-step setup script.
Run this once to verify everything is working before ingestion.
Each step explains what it does, why, and what to do if it fails.
"""
import sys
import os

# These three env vars are read by Google SDKs and ADK directly.
# They are NOT app settings so they don't go in .env / settings.py.
# We set them here so the whole script runs in Vertex AI mode (no API key needed).
os.environ["GOOGLE_CLOUD_PROJECT"] = "unfair-advantage-6"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

# ── helpers ──────────────────────────────────────────────────────────────────

def step(n, title):
    print(f"\n{'='*60}")
    print(f"  STEP {n}: {title}")
    print(f"{'='*60}")

def ok(msg):
    print(f"  ✓  {msg}")

def fail(msg, fix):
    print(f"  ✗  {msg}")
    print(f"  →  FIX: {fix}")
    sys.exit(1)

def info(msg):
    print(f"  ℹ  {msg}")

def pause(msg="Press Enter to continue..."):
    input(f"\n  ▶  {msg}")

# ── Step 1: Settings ──────────────────────────────────────────────────────────

step(1, "Load settings from .env")
info("Reading all config values from your .env file via pydantic-settings.")
info("If this fails, a required variable is missing or misnamed.")

try:
    from config.settings import settings
    ok(f"GCP Project     : {settings.gcp_project_id}")
    ok(f"GCP Region      : {settings.gcp_region}")
    ok(f"GCS Bucket      : {settings.gcs_bucket_name}")
    ok(f"Vertex Location : {settings.vertex_ai_location}")
    ok(f"RAG Corpus Name : {settings.vertex_ai_rag_corpus_name}")
    ok(f"Embedding Model : {settings.vertex_ai_embedding_model}")
    ok(f"Gemini Root     : {settings.gemini_model_root}")
    ok(f"Neo4j URI       : {settings.neo4j_uri[:40]}...")
except Exception as e:
    fail(str(e), "Check your .env file — compare with .env.example")

pause()

# ── Step 2: ADC ───────────────────────────────────────────────────────────────

step(2, "Verify Google Cloud ADC (Application Default Credentials)")
info("ADC is how your Python code authenticates to Google Cloud.")
info("It reads a credentials file saved by 'gcloud auth application-default login'.")
info("No API key needed — your Google account IS the credential.")

try:
    import google.auth
    credentials, project = google.auth.default()
    ok(f"ADC credentials found")
    ok(f"Default project from ADC: {project or '(not set — using .env value)'}")
except Exception as e:
    fail(
        f"ADC not found: {e}",
        "Run: gcloud auth application-default login"
    )

pause()

# ── Step 3: GCS ───────────────────────────────────────────────────────────────

step(3, "Verify Google Cloud Storage bucket access")
info(f"Checking bucket: gs://{settings.gcs_bucket_name}")
info("This bucket stores your original PDFs and tracks which ones are processed.")
info("The ingestion pipeline uploads PDFs here before sending to Vertex AI RAG.")

try:
    from google.cloud import storage
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_bucket_name)
    if not bucket.exists():
        fail(
            f"Bucket '{settings.gcs_bucket_name}' does not exist",
            "Create it in Cloud Console → Cloud Storage → Create Bucket"
        )
    blobs = list(client.list_blobs(settings.gcs_bucket_name, max_results=5))
    ok(f"Bucket accessible: gs://{settings.gcs_bucket_name}")
    ok(f"Objects in bucket: {len(blobs)} (showing up to 5)")
    for b in blobs:
        info(f"  - {b.name}")
except Exception as e:
    fail(str(e), "Check bucket name in .env and ensure Cloud Storage API is enabled")

pause()

# ── Step 4: Vertex AI RAG ─────────────────────────────────────────────────────

step(4, "Verify Vertex AI RAG Engine access")
info("The RAG Engine is Vertex AI's managed vector database.")
info("It stores your book chunks as embeddings (numbers representing meaning).")
info("When you ask a question, it finds the most semantically similar chunks.")
info(f"Location: {settings.vertex_ai_location}")

try:
    import vertexai
    from vertexai.preview import rag
    vertexai.init(project=settings.gcp_project_id, location=settings.vertex_ai_location)
    corpora = list(rag.list_corpora())
    ok(f"Vertex AI RAG Engine accessible in {settings.vertex_ai_location}")
    if corpora:
        ok(f"Existing corpora found: {len(corpora)}")
        for c in corpora:
            info(f"  - {c.display_name} ({c.name.split('/')[-1]})")
    else:
        info("No corpora yet — will be created during ingestion")
except Exception as e:
    fail(
        str(e),
        "Ensure Vertex AI API is enabled: gcloud services enable aiplatform.googleapis.com"
    )

pause()

# ── Step 5: Gemini model ──────────────────────────────────────────────────────

step(5, "Test Gemini model via Vertex AI")
info(f"Testing model: {settings.gemini_model_root} in {settings.vertex_ai_location}")
info("The agent uses Gemini to reason over retrieved content and generate answers.")
info("We use Vertex AI (not Gemini API) so no API key is needed — just ADC.")

try:
    from google import genai as google_genai
    import asyncio

    async def test_gemini():
        client = google_genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )
        response = await client.aio.models.generate_content(
            model=settings.gemini_model_root,
            contents="Reply with exactly: WORKING"
        )
        return response.text.strip()

    result = asyncio.run(test_gemini())
    ok(f"Gemini response: {result}")
except Exception as e:
    fail(
        str(e),
        f"Model '{settings.gemini_model_root}' may not be available in {settings.vertex_ai_location}. "
        "Try changing VERTEX_AI_LOCATION in .env"
    )

pause()

# ── Step 6: Neo4j ─────────────────────────────────────────────────────────────

step(6, "Test Neo4j connection")
info("Neo4j is the graph database where Graphiti stores concept relationships.")
info("It maps how ideas connect across books — e.g. dharma → duty → Arjuna.")
info("Currently graph building is skipped due to embedding quota, but connection is tested.")

try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    with driver.session(database=settings.neo4j_database) as session:
        result = session.run("RETURN 1 AS n")
        val = result.single()["n"]
        assert val == 1
    driver.close()
    ok(f"Neo4j connected: {settings.neo4j_uri[:40]}...")
except Exception as e:
    fail(
        str(e),
        "Check NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD in .env. "
        "Ensure AuraDB instance is running."
    )

pause()

# ── Step 7: Books folder ──────────────────────────────────────────────────────

step(7, "Check books folder for PDFs to ingest")
info("Drop your PDF books in the 'books/' folder.")
info("The ingestion pipeline reads from here, uploads to GCS, then indexes in Vertex AI RAG.")

books_dir = "books"
if not os.path.exists(books_dir):
    os.makedirs(books_dir)
    info("Created books/ folder (was missing)")

pdfs = [f for f in os.listdir(books_dir) if f.endswith(".pdf")]
if pdfs:
    ok(f"Found {len(pdfs)} PDF(s) ready to ingest:")
    for pdf in pdfs:
        size_mb = os.path.getsize(os.path.join(books_dir, pdf)) / 1024 / 1024
        info(f"  - {pdf} ({size_mb:.1f} MB)")
else:
    info("No PDFs found in books/ folder")
    info("Add a PDF and run: python -m ingestion.pipeline --file books/your_book.pdf")

# ── Done ──────────────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print("  ALL CHECKS PASSED")
print(f"{'='*60}")
print()
print("  Next steps:")
print("  1. Add PDFs to books/ folder")
print("  2. Run ingestion:")
print("     $env:SKIP_GRAPH_BUILDING='true'")
print("     python -m ingestion.pipeline --file books/your_book.pdf")
print()
print("  3. Start the agent:")
print("     $env:GOOGLE_GENAI_USE_VERTEXAI='true'")
print("     $env:GOOGLE_CLOUD_PROJECT='unfair-advantage-6'")
print("     $env:GOOGLE_CLOUD_LOCATION='us-central1'")
print("     venv\\Scripts\\adk api_server --port 8080 .")
print()
print("  4. Ask a question:")
print('     curl -X POST http://localhost:8080/run \\')
print('       -H "Content-Type: application/json" \\')
print('       -d "{\\"app_name\\":\\"agent\\",\\"user_id\\":\\"u1\\",\\"session_id\\":\\"s1\\",\\"new_message\\":{\\"role\\":\\"user\\",\\"parts\\":[{\\"text\\":\\"What does the Gita say about duty?\\"}]}}"')
print()
