"""
Language Detection Engine for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
Supports English, Hindi, Hinglish, Telugu, Tamil, and Odia.
"""
import re
from typing import Optional, Dict
from .interfaces import ILanguageDetector
from .models import LanguageResult
from .config import speech_config


class LanguageDetector(ILanguageDetector):
    """
    Automatic spoken/text language detector supporting J.A.R.V.I.S. languages.
    Uses phonetic script signatures and vocabulary markers for low-latency classification.
    """

    SCRIPT_PATTERNS: Dict[str, str] = {
        "hindi": r"[\u0900-\u097F]",      # Devanagari
        "telugu": r"[\u0C00-\u0C7F]",     # Telugu script
        "tamil": r"[\u0B80-\u0BFF]",      # Tamil script
        "odia": r"[\u0B00-\u0B7F]",       # Odia script
    }

    HINGLISH_WORDS = {
        "kya", "kaise", "batao", "karo", "kya", "hai", "mujhe", "tum", "apna", "haan",
        "nahi", "karna", "ho", "gaya", "chahiye", "kar"
    }

    def detect_language(self, audio_bytes: bytes, text_sample: Optional[str] = None) -> LanguageResult:
        if not text_sample:
            return LanguageResult(
                language=speech_config.default_language,
                confidence=0.8,
                is_fallback=True,
            )

        text = text_sample.strip()
        if not text:
            return LanguageResult(
                language=speech_config.default_language,
                confidence=0.8,
                is_fallback=True,
            )

        # 1. Check native non-Latin script patterns
        for lang, pattern in self.SCRIPT_PATTERNS.items():
            if re.search(pattern, text):
                return LanguageResult(language=lang, confidence=0.95, is_fallback=False)

        # 2. Check Hinglish Romanized Hindi vocabulary heuristics
        words = [w.lower() for w in re.findall(r"\b\w+\b", text)]
        if words:
            hinglish_count = sum(1 for w in words if w in self.HINGLISH_WORDS)
            ratio = hinglish_count / len(words)
            if ratio >= 0.2:
                return LanguageResult(language="hinglish", confidence=0.88, is_fallback=False)

        # 3. Default to English
        return LanguageResult(
            language="english",
            confidence=0.95,
            is_fallback=False,
        )

    def reset(self) -> None:
        pass
