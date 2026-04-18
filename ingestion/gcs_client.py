"""
GCS client — upload PDFs, check if already processed, mark as done.
Auth comes from gcloud ADC (no key needed in .env).
"""
import json
from pathlib import Path
from loguru import logger
from google.cloud import storage
from config.settings import settings

_client: storage.Client | None = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client(project=settings.gcp_project_id)
    return _client


def upload_book(local_path: str | Path) -> str:
    """Upload a PDF to GCS books/ folder. Returns the GCS URI."""
    local_path = Path(local_path)
    bucket = _get_client().bucket(settings.gcs_bucket_name)
    blob_name = f"books/{local_path.name}"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path), content_type="application/pdf")
    gcs_uri = f"gs://{settings.gcs_bucket_name}/{blob_name}"
    logger.info(f"Uploaded {local_path.name} → {gcs_uri}")
    return gcs_uri


def is_processed(filename: str) -> bool:
    """Check if a book has already been ingested."""
    bucket = _get_client().bucket(settings.gcs_bucket_name)
    blob = bucket.blob(f"processed/{Path(filename).stem}.json")
    return blob.exists()


def mark_processed(filename: str, metadata: dict) -> None:
    """Write a small JSON marker so we skip re-ingestion."""
    bucket = _get_client().bucket(settings.gcs_bucket_name)
    blob = bucket.blob(f"processed/{Path(filename).stem}.json")
    blob.upload_from_string(json.dumps(metadata, indent=2), content_type="application/json")
    logger.info(f"Marked {filename} as processed")


def list_unprocessed_books() -> list[str]:
    """Return GCS URIs of books not yet ingested."""
    client = _get_client()
    bucket = client.bucket(settings.gcs_bucket_name)
    all_books = [
        b.name for b in bucket.list_blobs(prefix="books/")
        if b.name.endswith(".pdf")
    ]
    unprocessed = [
        f"gs://{settings.gcs_bucket_name}/{name}"
        for name in all_books
        if not is_processed(Path(name).name)
    ]
    return unprocessed
