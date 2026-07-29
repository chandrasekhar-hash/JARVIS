"""
Hybrid Non-Vector Search Engine for Phase P1.2 (Memory & Personalization).
Performs multi-field keyword matching, tag filtering, category weighting, recency decay,
and importance/confidence score ranking across user-scoped memories.
"""
import time
import logging
from typing import Optional, List, Dict, Any, Tuple

from .memory_models import (
    Memory,
    MemoryCategory,
    MemoryType,
    MemoryStatus,
    MemorySearchResult,
)
from .memory_interfaces import IMemorySearchEngine, IMemoryRepository

logger = logging.getLogger("JARVIS_MemorySearchEngine")


class MemorySearchEngine(IMemorySearchEngine):
    """
    Hybrid non-vector search engine.
    Computes relevancy scores based on text matching, tag overlap, category affinity,
    pinned status, importance, and confidence scores. Designed to seamlessly integrate
    future vector embedding search without breaking APIs.
    """

    def __init__(self, repository: IMemoryRepository):
        self.repository = repository

    def search_memories(
        self,
        user_id: str,
        query: str,
        category: Optional[MemoryCategory] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> MemorySearchResult:
        """
        Performs hybrid multi-field search and returns ranked MemorySearchResult.
        """
        start_time = time.time()
        # Fetch candidate active memories for user
        candidates = self.repository.list_memories(
            user_id=user_id,
            category=category,
            status=MemoryStatus.ACTIVE,
            limit=500,
        )

        query_terms = [t.strip().lower() for t in query.split()] if query else []
        filter_tags = [t.strip().lower() for t in (tags or [])]

        scored_memories: List[Tuple[float, Memory]] = []

        for mem in candidates:
            # If tag filtering requested, skip memory if it has no matching tags
            if filter_tags:
                mem_tags_clean = [t.strip().lower() for t in (mem.tags or [])]
                matching_tags = set(filter_tags).intersection(mem_tags_clean)
                if not matching_tags:
                    continue
            else:
                matching_tags = set()

            score = 0.0

            # 1. Pinned Boost
            if mem.is_pinned:
                score += 5.0

            # 2. Importance and Confidence Weighting
            score += mem.importance_score * 2.0
            score += mem.confidence_score * 1.5

            # 3. Category Match Weighting
            if category and mem.category == category:
                score += 2.0

            # 4. Tag Match Weighting
            if matching_tags:
                score += len(matching_tags) * 3.0

            # 5. Keyword Text Matching
            if query_terms:
                title_clean = mem.title.lower()
                content_clean = mem.content.lower()

                title_matches = sum(1 for term in query_terms if term in title_clean)
                content_matches = sum(1 for term in query_terms if term in content_clean)

                if title_matches == 0 and content_matches == 0 and not filter_tags:
                    continue  # Skip un-matched memories if a query term was specified

                score += title_matches * 4.0
                score += content_matches * 1.5

            scored_memories.append((score, mem))

        # Sort descending by score
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        results = [mem for score, mem in scored_memories[:limit]]

        elapsed_ms = (time.time() - start_time) * 1000.0
        return MemorySearchResult(
            memories=results,
            total_count=len(results),
            query=query,
            search_time_ms=elapsed_ms,
        )
