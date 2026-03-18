"""
Embedding service for ScholarMind.
Uses sentence-transformers to generate dense vector embeddings.
"""

from sentence_transformers import SentenceTransformer
import config

# Load model once at module level (cached after first import)
print(f"[Embeddings] Loading model '{config.EMBEDDING_MODEL}'...")
_model = SentenceTransformer(config.EMBEDDING_MODEL)
print(f"[Embeddings] Model loaded. Dimension: {config.EMBEDDING_DIMENSION}")


def embed_text(text: str) -> list:
    """
    Generate an embedding vector for a single text string.

    Args:
        text: input text to embed

    Returns:
        list of floats (384-dimensional for all-MiniLM-L6-v2)
    """
    embedding = _model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_batch(texts: list) -> list:
    """
    Generate embedding vectors for a batch of texts.

    Args:
        texts: list of strings to embed

    Returns:
        list of lists of floats
    """
    embeddings = _model.encode(texts, normalize_embeddings=True, batch_size=32)
    return embeddings.tolist()
