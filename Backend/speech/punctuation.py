"""
Transcript Cleanup & Punctuation Normalizer for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
"""
import re
from .interfaces import ITranscriptCleaner


class TranscriptCleaner(ITranscriptCleaner):
    """
    Cleans, formats, deduplicates repeated words, and capitalizes transcript text.
    Does NOT insert or hallucinate extra words.
    """

    def clean(self, text: str) -> str:
        if not text or not text.strip():
            return ""

        cleaned = text.strip()

        # 1. Normalize multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned)

        # 2. Deduplicate consecutive repeated words (case-insensitive e.g. "the the" -> "the")
        words = cleaned.split()
        deduped_words = []
        for w in words:
            if not deduped_words or deduped_words[-1].lower() != w.lower():
                deduped_words.append(w)

        cleaned = " ".join(deduped_words)

        # 3. Capitalize first letter of utterance if lowercased
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]

        # 4. Normalize spacing around punctuation
        cleaned = re.sub(r"\s+([.,?!])", r"\1", cleaned)

        return cleaned
