"""
JARVIS Product 1.6 - Semantic Dense Search Engine.
Executes vector similarity search using IEmbeddingProvider & IVectorStore.
"""

from typing import List, Dict, Any, Tuple, Optional
from ..interfaces import IVectorStore
from ..embedding import IEmbeddingProvider, EmbeddingCache


class SemanticSearchEngine:
    def __init__(self, vector_store: IVectorStore, embedding_cache: EmbeddingCache):
        self.vector_store = vector_store
        self.embedding_cache = embedding_cache

    def search(
        self,
        query: str,
        top_k: int = 10,
        allowed_doc_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        if not query or not query.strip():
            return []

        embeddings, _ = self.embedding_cache.get_embeddings([query])
        if not embeddings:
            return []

        query_vec = embeddings[0]
        filters = {"allowed_doc_ids": allowed_doc_ids} if allowed_doc_ids is not None else None
        return self.vector_store.search_vectors(query_vec, top_k=top_k, filters=filters)
