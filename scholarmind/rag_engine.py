"""
RAG (Retrieval-Augmented Generation) engine for ScholarMind.
Retrieves relevant context from Endee and generates answers using Groq LLM.
"""

from groq import Groq
import config
from embeddings import embed_text
from endee_client import vector_store


def retrieve_context(query: str, top_k: int = 5, filters: dict = None):
    """
    Retrieve relevant document chunks from Endee for a given query.

    Args:
        query: natural language question
        top_k: number of chunks to retrieve
        filters: optional Endee filter conditions

    Returns:
        list of result dicts with id, similarity, meta (including text)
    """
    query_vector = embed_text(query)
    results = vector_store.search(query_vector, top_k=top_k, filters=filters)
    return results


def generate_answer(query: str, context_chunks: list) -> dict:
    """
    Generate an answer using the Groq LLM with retrieved context.

    Args:
        query: the user's question
        context_chunks: list of result dicts from retrieve_context

    Returns:
        dict with 'answer', 'sources', and 'model'
    """
    if not config.GROQ_API_KEY or config.GROQ_API_KEY == "your-groq-api-key-here":
        return {
            "answer": "⚠️ RAG is not configured. Please set your GROQ_API_KEY in the .env file to enable AI-powered answers. You can get a free API key at https://console.groq.com",
            "sources": [],
            "model": "none",
        }

    # Build context string from retrieved chunks
    context_parts = []
    sources = []
    for i, chunk in enumerate(context_chunks):
        meta = chunk.get("meta", {})
        text = meta.get("text", "")
        source = meta.get("source", "unknown")
        similarity = chunk.get("similarity", 0)

        context_parts.append(f"[Source {i + 1}: {source} (relevance: {similarity:.2f})]\n{text}")

        if source not in [s["name"] for s in sources]:
            sources.append({"name": source, "similarity": round(similarity, 3)})

    context_str = "\n\n---\n\n".join(context_parts)

    # Build the prompt
    system_prompt = """You are ScholarMind, an intelligent research assistant. 
Answer the user's question based ONLY on the provided context documents. 
If the context doesn't contain enough information to answer the question, say so clearly.
Always cite which source(s) you used in your answer.
Be concise, accurate, and helpful. Use bullet points or numbered lists when appropriate."""

    user_prompt = f"""Context documents:

{context_str}

---

Question: {query}

Please provide a comprehensive answer based on the context above."""

    # Call Groq API
    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        answer = completion.choices[0].message.content

        return {
            "answer": answer,
            "sources": sources,
            "model": config.LLM_MODEL,
        }

    except Exception as e:
        return {
            "answer": f"Error generating answer: {str(e)}",
            "sources": sources,
            "model": config.LLM_MODEL,
        }


def rag_query(query: str, top_k: int = 5, filters: dict = None) -> dict:
    """
    End-to-end RAG pipeline: retrieve context → generate answer.

    Args:
        query: the user's natural language question
        top_k: number of context chunks to retrieve
        filters: optional filter conditions

    Returns:
        dict with 'answer', 'sources', 'context_chunks', 'model'
    """
    # 1. Retrieve relevant context
    context_chunks = retrieve_context(query, top_k=top_k, filters=filters)

    if not context_chunks:
        return {
            "answer": "I couldn't find any relevant documents in the knowledge base. Please upload some documents first, then try again.",
            "sources": [],
            "context_chunks": [],
            "model": "none",
        }

    # 2. Generate answer with LLM
    result = generate_answer(query, context_chunks)

    # 3. Include the raw context for the frontend to display
    result["context_chunks"] = [
        {
            "text": c.get("meta", {}).get("text", ""),
            "source": c.get("meta", {}).get("source", "unknown"),
            "similarity": round(c.get("similarity", 0), 3),
            "chunk_index": c.get("meta", {}).get("chunk_index", 0),
        }
        for c in context_chunks
    ]

    return result
