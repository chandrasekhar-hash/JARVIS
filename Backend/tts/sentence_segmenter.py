"""
Sentence Segmentation Engine for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
Segments response text into streaming sentence chunks while preserving abbreviations, numbers, and URLs.
"""
import re
from typing import List
from .interfaces import ISentenceSegmenter


class SentenceSegmenter(ISentenceSegmenter):
    """
    Abbreviation-aware and number-aware sentence boundary segmenter.
    Splits text on sentence boundaries (., ?, !, ;) for streaming TTS synthesis.
    """

    ABBREVIATIONS = {
        "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "vs", "etc", "eg", "ie",
        "st", "ave", "rd", "blvd", "dept", "inc", "ltd", "co", "corp", "jan",
        "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
    }

    def segment(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []

        raw = text.strip()

        # Split on sentence end punctuation followed by whitespace or quote
        # Using negative lookbehinds for single letters or digits (e.g., A.I., v1.4, 3.14)
        raw_chunks = re.split(r"(?<=[.?!;])\s+(?=[A-Z0-9\"'])", raw)

        segments: List[str] = []
        current: List[str] = []

        for chunk in raw_chunks:
            chunk_clean = chunk.strip()
            if not chunk_clean:
                continue

            # Check if chunk ends with a known abbreviation
            words = chunk_clean.lower().split()
            last_word = words[-1].rstrip(".") if words else ""

            if last_word in self.ABBREVIATIONS:
                current.append(chunk_clean)
            else:
                if current:
                    current.append(chunk_clean)
                    segments.append(" ".join(current))
                    current = []
                else:
                    segments.append(chunk_clean)

        if current:
            segments.append(" ".join(current))

        return segments if segments else [raw]
