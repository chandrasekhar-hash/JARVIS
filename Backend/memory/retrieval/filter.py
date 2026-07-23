import time
from typing import List, Optional
from memory.models.query import MemoryResult
from tools.telemetry import log_structured, backend_log


class MemoryFilter:
    """
    Applies multi-stage policy filtering (Expiry, Privacy, Confidence, Relevance) to ranked
    candidate memories, removing candidates that violate policy criteria.
    """

    def __init__(
        self,
        min_relevance: float = 0.3,
        min_confidence: float = 0.5,
        allow_sensitive: bool = False,
        allow_private: bool = False
    ):
        self.min_relevance = min_relevance
        self.min_confidence = min_confidence
        self.allow_sensitive = allow_sensitive
        self.allow_private = allow_private

    def filter(self, ranked_candidates: List[MemoryResult], current_time: Optional[float] = None) -> List[MemoryResult]:
        """
        Executes sequential policy filters against candidate memories.
        """
        now = current_time or time.time()
        filtered_results = []
        filtered_counts = {"expired": 0, "privacy": 0, "confidence": 0, "relevance": 0}

        for res in ranked_candidates:
            mem = res.memory
            meta = mem.metadata

            # 1. EXPIRY FILTER
            if meta.expires_at is not None and meta.expires_at < now:
                filtered_counts["expired"] += 1
                continue

            # 2. PRIVACY FILTER
            if meta.privacy_level == "private" and not self.allow_private:
                filtered_counts["privacy"] += 1
                continue
            if meta.privacy_level == "sensitive" and not self.allow_sensitive:
                filtered_counts["privacy"] += 1
                continue

            # 3. CONFIDENCE FILTER
            if meta.confidence < self.min_confidence:
                filtered_counts["confidence"] += 1
                continue

            # 4. RELEVANCE SCORE FILTER
            if res.score < self.min_relevance:
                filtered_counts["relevance"] += 1
                continue

            filtered_results.append(res)

        log_structured(
            backend_log,
            "INFO",
            f"[MemoryFilter] Filtered candidate pool: Retained {len(filtered_results)}/{len(ranked_candidates)} memories "
            f"(Dropped: {filtered_counts})"
        )
        return filtered_results
