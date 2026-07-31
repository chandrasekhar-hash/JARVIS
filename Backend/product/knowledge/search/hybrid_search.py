"""
JARVIS Product 1.6 - Hybrid Search Engine & Reciprocal Rank Fusion (RRF).
Merges semantic dense and sparse keyword rankings using RRF scoring: RRF(d) = sum(1 / (60 + r_m(d))).
"""

from typing import List, Dict, Any, Tuple, Optional
from .semantic_search import SemanticSearchEngine
from .keyword_search import KeywordSearchEngine


class HybridSearchEngine:
    def __init__(
        self,
        semantic_engine: SemanticSearchEngine,
        keyword_engine: KeywordSearchEngine,
        rrf_k: int = 60,
    ):
        self.semantic_engine = semantic_engine
        self.keyword_engine = keyword_engine
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 10,
        allowed_doc_ids: Optional[List[str]] = None,
        candidate_multiplier: int = 3,
    ) -> List[Tuple[str, float]]:
        candidate_k = top_k * candidate_multiplier

        # 1. Fetch dense candidates
        dense_results = self.semantic_engine.search(
            query=query,
            top_k=candidate_k,
            allowed_doc_ids=allowed_doc_ids,
        )

        # 2. Fetch sparse candidates
        sparse_results = self.keyword_engine.search(
            query=query,
            top_k=candidate_k,
            allowed_doc_ids=allowed_doc_ids,
        )

        # 3. Compute Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}

        # Process dense ranks
        for rank, (chk_id, _) in enumerate(dense_results):
            score = 1.0 / (self.rrf_k + (rank + 1))
            rrf_scores[chk_id] = rrf_scores.get(chk_id, 0.0) + score

        # Process sparse ranks
        for rank, (chk_id, _) in enumerate(sparse_results):
            score = 1.0 / (self.rrf_k + (rank + 1))
            rrf_scores[chk_id] = rrf_scores.get(chk_id, 0.0) + score

        # Sort merged candidate list
        ranked_chunks = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        return ranked_chunks[:top_k]
