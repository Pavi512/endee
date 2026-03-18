"""
Centralized configuration for ScholarMind.
Loads from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Endee Vector Database ──────────────────────────────────────────
ENDEE_HOST = os.getenv("ENDEE_HOST", "http://localhost")
ENDEE_PORT = int(os.getenv("ENDEE_PORT", "8080"))
ENDEE_BASE_URL = f"{ENDEE_HOST}:{ENDEE_PORT}/api/v1"

# ── Index Settings ─────────────────────────────────────────────────
INDEX_NAME = os.getenv("INDEX_NAME", "scholarmind_docs")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))
SPACE_TYPE = "cosine"

# ── Embedding Model ───────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ── LLM / RAG ─────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

# ── Flask ──────────────────────────────────────────────────────────
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

# ── Chunking ──────────────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ── Upload ─────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
