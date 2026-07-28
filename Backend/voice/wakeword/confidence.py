import time
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("JARVIS_ConfidenceEngine")


class ConfidenceEngine:
    """
    Confidence Scoring Engine evaluating candidate wake word acoustic features,
    spectral energy, and phonetic matching against configured activation thresholds.
    """

    def __init__(self, default_threshold: float = 0.75):
        self.threshold = default_threshold

    def set_threshold(self, new_threshold: float):
        self.threshold = max(0.1, min(0.99, new_threshold))
        logger.info(f"Updated wake word confidence threshold to: {self.threshold:.2f}")

    def evaluate_match(
        self,
        keyword: str,
        raw_score: float,
        audio_duration: float,
        energy_level: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluates candidate match and returns (is_above_threshold, match_metadata).
        """
        # Dynamic weighting based on energy level & raw match score
        energy_penalty = 0.0 if energy_level > 0.01 else 0.15
        final_confidence = max(0.0, min(1.0, raw_score - energy_penalty))
        is_above = final_confidence >= self.threshold

        decision = "ACTIVATE" if is_above else "REJECT"

        metadata = {
            "keyword": keyword,
            "confidence": round(final_confidence, 4),
            "raw_score": round(raw_score, 4),
            "threshold": self.threshold,
            "duration_seconds": round(audio_duration, 3),
            "energy_level": round(energy_level, 4),
            "timestamp": time.time(),
            "decision": decision
        }

        if is_above:
            logger.info(f"Wake word '{keyword}' ACTIVATED with confidence {final_confidence:.2f} (Threshold: {self.threshold:.2f})")
        else:
            logger.debug(f"Wake word '{keyword}' REJECTED with confidence {final_confidence:.2f} (Threshold: {self.threshold:.2f})")

        return is_above, metadata


confidence_engine = ConfidenceEngine()
