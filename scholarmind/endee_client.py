"""
Endee vector database client wrapper for ScholarMind.
Handles index creation, upserting vectors, and querying.
"""

from endee import Endee, Precision
import config


class EndeeVectorStore:
    """Wrapper around the Endee Python SDK for vector operations."""

    def __init__(self):
        self.client = Endee()
        self.client.set_base_url(config.ENDEE_BASE_URL)
        self.index_name = config.INDEX_NAME
        self.dimension = config.EMBEDDING_DIMENSION
        self._index = None

    def ensure_index(self):
        """Create the index if it doesn't already exist."""
        try:
            self._index = self.client.get_index(name=self.index_name)
            print(f"[Endee] Index '{self.index_name}' already exists.")
        except Exception:
            print(f"[Endee] Creating index '{self.index_name}' ...")
            self.client.create_index(
                name=self.index_name,
                dimension=self.dimension,
                space_type=config.SPACE_TYPE,
                precision=Precision.FLOAT32,
            )
            self._index = self.client.get_index(name=self.index_name)
            print(f"[Endee] Index '{self.index_name}' created successfully.")

    def _get_index(self):
        """Return the cached index handle, creating if needed."""
        if self._index is None:
            self.ensure_index()
        return self._index

    def upsert_chunks(self, chunks):
        """
        Upsert a list of document chunks into Endee.

        Args:
            chunks: list of dicts with keys:
                - id (str)
                - vector (list[float])
                - meta (dict) with keys like 'text', 'source', 'category', 'chunk_index'
        """
        index = self._get_index()

        # Batch upsert in groups of 100
        batch_size = 100
        
        # Monkey-patch VectorItem to support .get() due to a bug in Endee 0.1.19
        try:
            from endee.schema import VectorItem
            if not hasattr(VectorItem, "get"):
                def _mock_get(self, key, default=None):
                    return getattr(self, key, default)
                VectorItem.get = _mock_get
        except ImportError:
            pass
            
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            records = []
            for chunk in batch:
                records.append(
                    {
                        "id": chunk["id"],
                        "vector": chunk["vector"],
                        "meta": chunk.get("meta", {}),
                    }
                )
            
            index.upsert(records)
            print(f"[Endee] Upserted batch {i // batch_size + 1} ({len(batch)} vectors)")

        return len(chunks)

    def search(self, query_vector, top_k=5, filters=None):
        """
        Search for similar vectors in the index.

        Args:
            query_vector: list[float] — the query embedding
            top_k: number of results to return
            filters: optional dict of filter conditions

        Returns:
            list of result dicts with id, similarity, meta
        """
        index = self._get_index()

        try:
            if filters:
                results = index.query(
                    vector=query_vector,
                    top_k=top_k,
                    filters=filters,
                )
            else:
                results = index.query(
                    vector=query_vector,
                    top_k=top_k,
                )

            # Normalize results to a consistent format
            formatted = []
            for r in results:
                formatted.append(
                    {
                        "id": r.get("id", ""),
                        "similarity": r.get("similarity", 0.0),
                        "meta": r.get("meta", {}),
                    }
                )
            return formatted

        except Exception as e:
            print(f"[Endee] Search error: {e}")
            return []

    def get_stats(self):
        """Return basic index statistics."""
        try:
            index = self._get_index()
            info = self.client.get_index(name=self.index_name)
            return {
                "index_name": self.index_name,
                "dimension": self.dimension,
                "status": "connected",
            }
        except Exception as e:
            return {
                "index_name": self.index_name,
                "status": "error",
                "error": str(e),
            }

    def health_check(self):
        """Check if Endee is reachable."""
        try:
            self.client.get_index(name=self.index_name)
            return True
        except Exception:
            # Even if index doesn't exist, try listing indexes
            try:
                import requests
                resp = requests.get(f"{config.ENDEE_BASE_URL}/indexes", timeout=5)
                return resp.status_code == 200
            except Exception:
                return False


# Module-level singleton
vector_store = EndeeVectorStore()
