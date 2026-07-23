import hashlib
import difflib
from typing import List, Tuple, Optional
from memory.ingestion.capture import RawObservation
from memory.models.memory import Memory


class ObservationDeduplicator:
    """
    Detects exact and near-duplicate observations against existing memories to prevent
    redundant storage in the Memory subsystem.
    """

    def __init__(self, similarity_threshold: float = 0.90):
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def compute_content_hash(text: str) -> str:
        """Computes SHA-256 hash of normalized lowercase whitespace-stripped content."""
        clean_text = " ".join(text.lower().strip().split())
        return hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculates SequenceMatcher ratio between two text strings."""
        s1 = " ".join(text1.lower().strip().split())
        s2 = " ".join(text2.lower().strip().split())
        if not s1 or not s2:
            return 0.0
        return difflib.SequenceMatcher(None, s1, s2).ratio()

    def is_duplicate(self, observation: RawObservation, existing_memories: List[Memory]) -> Tuple[bool, Optional[str]]:
        """
        Checks if observation is an exact or near duplicate of any existing memory.
        Returns (is_duplicate: bool, matched_memory_id: str or None).
        """
        obs_hash = self.compute_content_hash(observation.content)

        for mem in existing_memories:
            # 1. Exact Content Hash Check
            mem_hash = self.compute_content_hash(mem.content)
            if obs_hash == mem_hash:
                return True, mem.memory_id

            # 2. Near-Duplicate Similarity Check
            sim_score = self.calculate_similarity(observation.content, mem.content)
            if sim_score >= self.similarity_threshold:
                return True, mem.memory_id

        return False, None
