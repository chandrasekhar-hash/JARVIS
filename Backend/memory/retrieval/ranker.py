import time
import math
from typing import List, Dict, Any, Optional
from memory.models.query import MemoryResult
from tools.telemetry import log_structured, backend_log


class RankingWeights:
    def __init__(
        self,
        w_sim: float = 0.40,
        w_rec: float = 0.25,
        w_imp: float = 0.15,
        w_freq: float = 0.10,
        w_conf: float = 0.10
    ):
        self.w_sim = w_sim
        self.w_rec = w_rec
        self.w_imp = w_imp
        self.w_freq = w_freq
        self.w_conf = w_conf


class MemoryRanker:
    """
    Multi-factor ranking engine computing composite scores based on similarity, recency decay,
    importance rating, historical access frequency, and confidence.
    """

    def __init__(self, weights: Optional[RankingWeights] = None):
        self.weights = weights or RankingWeights()

    @staticmethod
    def calculate_recency_score(last_accessed: float, current_time: float, half_life_days: float = 30.0) -> float:
        """Calculates exponential recency decay score in range (0.0, 1.0]."""
        elapsed_seconds = max(0.0, current_time - last_accessed)
        half_life_seconds = half_life_days * 86400.0
        decay_rate = math.log(2) / half_life_seconds
        return math.exp(-decay_rate * elapsed_seconds)

    def rank(self, candidate_results: List[MemoryResult], current_time: Optional[float] = None) -> List[MemoryResult]:
        """
        Computes composite ranking score for each candidate and returns list sorted descending by score.
        """
        now = current_time or time.time()
        w = self.weights
        ranked_results = []

        for res in candidate_results:
            mem = res.memory
            meta = mem.metadata

            # 1. Similarity Score (S_sim)
            s_sim = max(0.0, min(1.0, res.score))

            # 2. Recency Score (S_rec)
            s_rec = self.calculate_recency_score(meta.last_accessed, now)

            # 3. Importance Score (S_imp): Normalized 1.0..10.0 -> 0.1..1.0
            s_imp = max(0.1, min(1.0, meta.importance_score / 10.0))

            # 4. Access Frequency Score (S_freq): Logarithmic scaling min(1.0, log(access_count + 1) / log(10))
            s_freq = min(1.0, math.log(meta.access_count + 1) / math.log(10)) if meta.access_count > 0 else 0.1

            # 5. Confidence Score (S_conf)
            s_conf = max(0.0, min(1.0, meta.confidence))

            # Composite Score Formula
            composite_score = (
                (w.w_sim * s_sim) +
                (w.w_rec * s_rec) +
                (w.w_imp * s_imp) +
                (w.w_freq * s_freq) +
                (w.w_conf * s_conf)
            )

            # Create new MemoryResult with updated composite score
            ranked_results.append(
                MemoryResult(
                    memory=mem,
                    score=round(composite_score, 4),
                    matched_by=res.matched_by
                )
            )

        # Sort descending by composite score
        ranked_results.sort(key=lambda r: r.score, reverse=True)
        log_structured(backend_log, "INFO", f"[MemoryRanker] Ranked {len(ranked_results)} memory candidates")
        return ranked_results
