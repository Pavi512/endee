"""
Document loader and chunker for ScholarMind.
Handles PDF, TXT, and MD file parsing and text chunking.
"""

import os
import uuid
import PyPDF2
import config
from embeddings import embed_batch


def load_file(filepath: str) -> str:
    """
    Read text content from a file (PDF, TXT, or MD).

    Args:
        filepath: path to the file

    Returns:
        extracted text as a string
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return _load_pdf(filepath)
    elif ext in (".txt", ".md"):
        return _load_text(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _load_pdf(filepath: str) -> str:
    """Extract text from a PDF file."""
    text_parts = []
    with open(filepath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    return "\n\n".join(text_parts)


def _load_text(filepath: str) -> str:
    """Read a plain text or markdown file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list:
    """
    Split text into overlapping chunks using a sliding window.

    Args:
        text: full document text
        chunk_size: max characters per chunk (default from config)
        overlap: character overlap between chunks (default from config)

    Returns:
        list of text chunks
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    # Clean up whitespace
    text = " ".join(text.split())

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < len(text):
            # Look for the last period, question mark, or newline within the chunk
            for sep in [". ", "? ", "! ", "\n"]:
                last_sep = text.rfind(sep, start + chunk_size // 2, end)
                if last_sep != -1:
                    end = last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward by (chunk_size - overlap)
        start = end - overlap if end < len(text) else len(text)

    return chunks


def process_document(filepath: str, category: str = "general", filename: str = None):
    """
    Full document processing pipeline:
    1. Load file → 2. Chunk text → 3. Generate embeddings → 4. Return records

    Args:
        filepath: path to the document file
        category: document category for filtering
        filename: original filename (for metadata)

    Returns:
        list of dicts ready for Endee upsert:
        [{"id": ..., "vector": [...], "meta": {"text": ..., "source": ..., ...}}]
    """
    source_name = filename or os.path.basename(filepath)

    # 1. Load
    print(f"[DataLoader] Loading '{source_name}'...")
    text = load_file(filepath)

    if not text.strip():
        print(f"[DataLoader] Warning: '{source_name}' is empty.")
        return []

    # 2. Chunk
    chunks = chunk_text(text)
    print(f"[DataLoader] Split into {len(chunks)} chunks.")

    # 3. Embed
    print(f"[DataLoader] Generating embeddings for {len(chunks)} chunks...")
    vectors = embed_batch([c for c in chunks])

    # 4. Build records
    doc_id = uuid.uuid4().hex[:8]
    records = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        records.append(
            {
                "id": f"{doc_id}_chunk_{i}",
                "vector": vector,
                "meta": {
                    "text": chunk,
                    "source": source_name,
                    "category": category,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            }
        )

    print(f"[DataLoader] Processed '{source_name}': {len(records)} records ready.")
    return records
