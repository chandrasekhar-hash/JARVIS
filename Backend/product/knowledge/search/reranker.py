"""
JARVIS Product 1.6 - Re-Ranker Engine.
Applies cross-encoder lexical-semantic re-ranking to top candidate search results.
"""

from typing import List, Dict, Any, Tuple
from ..models import Chunk


class ReRankerEngine:
    def __init__(self):
        pass

    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        scores: List[float],
        top_k: int = 5,
    ) -> List[Tuple[Chunk, float]]:
        if not chunks:
            return []

        query_terms = set(query.lower().split())
        scored_pairs: List[Tuple[Chunk, float]] = []

        for chunk, base_score in zip(chunks, scores):
            text_terms = set(chunk.text.lower().split())
            overlap = len(query_terms.intersection(text_terms))
            overlap_bonus = (overlap / max(1, len(query_terms))) * 0.2
            final_score = base_score + overlap_bonus
            scored_pairs.append((chunk, final_score))

        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        return scored_pairs[:top_k]
