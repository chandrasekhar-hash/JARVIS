"""
Partial Transcript Accumulator & Deduplicator for J.A.R.V.I.S. Phase V1.2 Speech Recognition Engine.
"""
from typing import List
from .interfaces import ITranscriptBuffer


class TranscriptBuffer(ITranscriptBuffer):
    """
    Accumulates streaming partial transcript updates and produces clean, deduplicated stable text.
    Eliminates token flicker and word repetitions using word-level overlap matching.
    """

    def __init__(self):
        self._stable_tokens: List[str] = []
        self._current_partial: str = ""
        self._confidence: float = 1.0

    def _deduplicate_overlap(self, existing_tokens: List[str], new_tokens: List[str]) -> List[str]:
        """Finds maximum suffix-prefix overlap between existing and new word sequences."""
        if not existing_tokens:
            return list(new_tokens)
        if not new_tokens:
            return list(existing_tokens)

        max_overlap = 0
        min_len = min(len(existing_tokens), len(new_tokens))

        for k in range(1, min_len + 1):
            if existing_tokens[-k:] == new_tokens[:k]:
                max_overlap = k

        if max_overlap > 0:
            return existing_tokens + new_tokens[max_overlap:]
        else:
            # If no overlap, check if new_tokens is an extension or replacement
            if len(new_tokens) >= len(existing_tokens) and new_tokens[: len(existing_tokens)] == existing_tokens:
                return list(new_tokens)
            return existing_tokens + [t for t in new_tokens if t not in existing_tokens]

    def add_partial(self, text: str, confidence: float = 1.0) -> str:
        self._current_partial = text.strip()
        self._confidence = confidence

        if not self._current_partial:
            return " ".join(self._stable_tokens)

        new_tokens = self._current_partial.split()
        self._stable_tokens = self._deduplicate_overlap(self._stable_tokens, new_tokens)
        return " ".join(self._stable_tokens)

    def finalize(self) -> str:
        final_text = " ".join(self._stable_tokens) if self._stable_tokens else self._current_partial
        self.reset()
        return final_text

    def get_current_transcript(self) -> str:
        if self._stable_tokens:
            return " ".join(self._stable_tokens)
        return self._current_partial

    def reset(self) -> None:
        self._stable_tokens.clear()
        self._current_partial = ""
        self._confidence = 1.0
