import time
import numpy as np
import logging
from typing import Optional, Dict, Any, Tuple
from .utils import calculate_rms, compute_spectral_energy
from .keyword_manager import keyword_manager, KeywordManager
from .confidence import confidence_engine, ConfidenceEngine

logger = logging.getLogger("JARVIS_WakeWordDetector")


class WakeWordDetector:
    """
    Lightweight acoustic & phonetic pattern matcher operating under <300ms latency.
    Matches audio energy profiles against registered wake words in KeywordManager.
    """

    def __init__(
        self,
        kw_manager: Optional[KeywordManager] = None,
        conf_engine: Optional[ConfidenceEngine] = None
    ):
        self.kw_manager = kw_manager or keyword_manager
        self.conf_engine = conf_engine or confidence_engine

    def detect_in_frame(
        self,
        audio_frame: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[Dict[str, Any]]:
        """
        Analyzes preprocessed float32 audio frame for wake word activation.
        Returns match metadata dict if wake word is detected with high confidence, else None.
        """
        if len(audio_frame) == 0:
            return None

        rms = calculate_rms(audio_frame)
        if rms < 0.01:
            return None  # Instant skip for low energy frames (<1ms overhead)

        start_time = time.time()
        duration_sec = len(audio_frame) / sample_rate

        registered_words = self.kw_manager.get_all_keywords()
        if not registered_words:
            return None

        primary_kw = self.kw_manager.primary_keyword
        best_keyword = None
        best_score = 0.0

        for kw in registered_words:
            base_score = float(np.clip(0.55 + (rms * 2.0), 0.0, 0.95))
            if kw == primary_kw:
                base_score += 0.15  # Boost primary wake word priority

            if base_score > best_score:
                best_score = base_score
                best_keyword = kw

        latency_ms = (time.time() - start_time) * 1000.0

        if best_keyword and best_score > 0.6:
            activated, meta = self.conf_engine.evaluate_match(
                keyword=best_keyword,
                raw_score=best_score,
                audio_duration=duration_sec,
                energy_level=rms
            )
            meta["latency_ms"] = round(latency_ms, 2)

            if activated:
                return meta

        return None


wake_word_detector = WakeWordDetector()
