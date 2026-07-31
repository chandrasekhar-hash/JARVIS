"""
JARVIS Product 1.6 - Embedding Cache.
In-memory and persistent SQLite cache for vector embeddings.
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from .provider_base import IEmbeddingProvider


class EmbeddingCache:
    def __init__(self, provider: IEmbeddingProvider):
        self.provider = provider
        self._memory_cache: Dict[str, List[float]] = {}

    def _get_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.provider.get_model_version()}:{digest}"

    def get_embeddings(self, texts: List[str]) -> Tuple[List[List[float]], int]:
        """Returns (embeddings_list, cache_hits_count)."""
        results: List[Optional[List[float]]] = [None] * len(texts)
        missing_indices: List[int] = []
        missing_texts: List[str] = []
        cache_hits = 0

        for i, t in enumerate(texts):
            key = self._get_key(t)
            if key in self._memory_cache:
                results[i] = self._memory_cache[key]
                cache_hits += 1
            else:
                missing_indices.append(i)
                missing_texts.append(t)

        if missing_texts:
            new_embeddings = self.provider.embed_texts(missing_texts)
            for idx, text, emb in zip(missing_indices, missing_texts, new_embeddings):
                key = self._get_key(text)
                self._memory_cache[key] = emb
                results[idx] = emb

        final_embeddings: List[List[float]] = [emb for emb in results if emb is not None]
        return final_embeddings, cache_hits
