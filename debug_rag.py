"""Debug RAG import issue."""
import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "unfair-advantage-6"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

import vertexai
from vertexai.preview import rag
from config.settings import settings

vertexai.init(project=settings.gcp_project_id, location=settings.vertex_ai_location)

# 1. List corpora
print("=== CORPORA ===")
for c in rag.list_corpora():
    print(f"  {c.display_name} -> {c.name}")

# 2. Get corpus
corpus = None
for c in rag.list_corpora():
    if c.display_name == settings.vertex_ai_rag_corpus_name:
        corpus = c
        break

if not corpus:
    print("No corpus found!")
    exit(1)

print(f"\n=== CORPUS DETAILS ===")
print(f"  Name: {corpus.name}")
print(f"  Display: {corpus.display_name}")
print(f"  Full object: {corpus}")

# 3. List files already in corpus
print(f"\n=== FILES IN CORPUS ===")
try:
    files = list(rag.list_files(corpus_name=corpus.name))
    print(f"  Total files: {len(files)}")
    for f in files:
        print(f"  - {f.display_name}: {f.state}")
except Exception as e:
    print(f"  Error listing files: {e}")

# 4. Try import with verbose error
print(f"\n=== ATTEMPTING IMPORT ===")
gcs_uri = f"gs://{settings.gcs_bucket_name}/books/Gitapress_Gita_Roman.pdf"
print(f"  URI: {gcs_uri}")
print(f"  Corpus: {corpus.name}")

try:
    result = rag.import_files(
        corpus_name=corpus.name,
        paths=[gcs_uri],
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    print(f"  Result: {result}")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    # print full traceback
    import traceback
    traceback.print_exc()
