"""
ScholarMind — Flask API Server
Semantic Knowledge Search & RAG Engine powered by Endee.
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

import config
from endee_client import vector_store
from embeddings import embed_text
from data_loader import process_document
from rag_engine import rag_query


# ── Flask App ──────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)


# ── Startup ────────────────────────────────────────────────────────
def initialize():
    """Initialize Endee index on startup."""
    try:
        vector_store.ensure_index()
        print("[ScholarMind] Endee index ready.")
    except Exception as e:
        print(f"[ScholarMind] Warning: Could not connect to Endee: {e}")
        print("[ScholarMind] Make sure Endee is running: docker compose up -d")


# ── Routes: Static ─────────────────────────────────────────────────
SAMPLE_DOCS_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/sample_docs/<path:filename>")
def serve_sample_doc(filename):
    """Serve sample documents for the 'Load Sample Documents' feature."""
    return send_from_directory(SAMPLE_DOCS_DIR, filename)


# ── Routes: Health ─────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    endee_ok = vector_store.health_check()
    llm_configured = bool(
        config.GROQ_API_KEY and config.GROQ_API_KEY != "your-groq-api-key-here"
    )
    return jsonify(
        {
            "status": "ok",
            "endee": "connected" if endee_ok else "disconnected",
            "llm": "configured" if llm_configured else "not configured",
            "index": config.INDEX_NAME,
        }
    )


# ── Routes: Upload ─────────────────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload_document():
    """Upload and index a document (PDF, TXT, or MD)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Check extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in config.ALLOWED_EXTENSIONS:
        return jsonify(
            {"error": f"Unsupported file type: .{ext}. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"}
        ), 400

    category = request.form.get("category", "general")

    # Save file temporarily
    filename = secure_filename(file.filename)
    filepath = os.path.join(config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        # Process: load → chunk → embed
        records = process_document(filepath, category=category, filename=filename)

        if not records:
            return jsonify({"error": "No content could be extracted from the file"}), 400

        # Upsert into Endee
        count = vector_store.upsert_chunks(records)

        return jsonify(
            {
                "message": f"Successfully indexed '{filename}'",
                "chunks": count,
                "category": category,
            }
        )

    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

    finally:
        # Clean up the uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)


# ── Routes: Search ─────────────────────────────────────────────────
@app.route("/api/search", methods=["POST"])
def search():
    """Semantic search across indexed documents."""
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    query = data["query"]
    top_k = data.get("top_k", 10)
    filters = data.get("filters", None)

    # Generate query embedding
    query_vector = embed_text(query)

    # Search Endee
    results = vector_store.search(query_vector, top_k=top_k, filters=filters)

    # Format response
    formatted_results = []
    for r in results:
        meta = r.get("meta", {})
        formatted_results.append(
            {
                "text": meta.get("text", ""),
                "source": meta.get("source", "unknown"),
                "category": meta.get("category", "general"),
                "similarity": round(r.get("similarity", 0), 4),
                "chunk_index": meta.get("chunk_index", 0),
            }
        )

    return jsonify(
        {
            "query": query,
            "results": formatted_results,
            "total": len(formatted_results),
        }
    )


# ── Routes: RAG Ask ────────────────────────────────────────────────
@app.route("/api/ask", methods=["POST"])
def ask():
    """Ask a question — RAG pipeline retrieves context and generates answer."""
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    query = data["query"]
    top_k = data.get("top_k", 5)
    filters = data.get("filters", None)

    result = rag_query(query, top_k=top_k, filters=filters)

    return jsonify(result)


# ── Routes: Stats ──────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def stats():
    """Return Endee index statistics."""
    return jsonify(vector_store.get_stats())


# ── Main ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    initialize()
    print(f"\n🧠 ScholarMind running at http://localhost:{config.FLASK_PORT}\n")
    app.run(
        host="0.0.0.0",
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
