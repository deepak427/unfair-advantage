"""
PDF → list of text chunks with metadata.
Uses PyMuPDF (fitz) for extraction, then splits by size with overlap.
"""
from dataclasses import dataclass, field
from pathlib import Path
import fitz  # PyMuPDF
from loguru import logger
from config.settings import settings


@dataclass
class Chunk:
    text: str
    book_title: str
    source_file: str
    page_start: int
    page_end: int
    chunk_index: int
    metadata: dict = field(default_factory=dict)


def extract_chunks(pdf_path: str | Path) -> list[Chunk]:
    """Extract and chunk text from a PDF file."""
    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))
    book_title = _get_title(doc, pdf_path)
    logger.info(f"Extracting '{book_title}' — {len(doc)} pages")

    # Step 1: extract full text per page
    pages: list[tuple[int, str]] = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append((page_num, text))
    doc.close()

    # Step 2: join all text, then split into overlapping chunks
    full_text = "\n\n".join(text for _, text in pages)
    raw_chunks = _split_text(full_text, settings.chunk_size, settings.chunk_overlap)

    # Step 3: wrap into Chunk dataclasses
    chunks = []
    for i, text in enumerate(raw_chunks):
        chunks.append(Chunk(
            text=text,
            book_title=book_title,
            source_file=pdf_path.name,
            page_start=1,   # fine-grained page tracking can be added later
            page_end=len(pages),
            chunk_index=i,
            metadata={
                "book_title": book_title,
                "source_file": pdf_path.name,
                "chunk_index": i,
                "total_chunks": len(raw_chunks),
            }
        ))

    logger.info(f"Created {len(chunks)} chunks from '{book_title}'")
    return chunks


def _get_title(doc: fitz.Document, path: Path) -> str:
    """Try PDF metadata first, fall back to filename."""
    meta = doc.metadata or {}
    return meta.get("title") or path.stem.replace("_", " ").replace("-", " ").title()


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks
