"""
JARVIS Product 1.6 - Keyword Sparse Search Engine.
Executes BM25 keyword matching via SQLiteMetadataStore FTS5 index.
"""

from typing import List, Dict, Any, Tuple, Optional
from ..interfaces import IMetadataStore


class KeywordSearchEngine:
    def __init__(self, metadata_store: IMetadataStore):
        self.metadata_store = metadata_store

    def search(
        self,
        query: str,
        top_k: int = 10,
        allowed_doc_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        if not query or not query.strip():
            return []

        return self.metadata_store.search_fts5_keywords(
            query=query,
            top_k=top_k,
            allowed_doc_ids=allowed_doc_ids,
        )
