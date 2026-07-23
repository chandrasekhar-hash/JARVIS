import re
from typing import Tuple, List
from memory.models.memory import MemoryType, MemoryMetadata, RetentionPolicy
from memory.ingestion.capture import RawObservation


class ObservationClassifier:
    """
    Rule-based classifier assigning MemoryType, importance rating, tags, and retention policies
    to incoming RawObservation instances without requiring external AI model calls.
    """

    PREFERENCE_KEYWORDS = [
        r"\bi prefer\b", r"\bi like\b", r"\bmy preference\b", r"\balways use\b",
        r"\bnever use\b", r"\bcall me\b", r"\bmy name is\b", r"\bvoice\b", r"\blanguage\b"
    ]

    PROJECT_KEYWORDS = [
        r"\brepository\b", r"\bcodebase\b", r"\bworkspace\b", r"\bgithub\b",
        r"\barchitecture\b", r"\bproject\b", r"\bsrc\b", r"\bbackend\b", r"\bfrontend\b"
    ]

    PROCEDURAL_KEYWORDS = [
        r"\bworkflow\b", r"\bmacro\b", r"\bsequence\b", r"\bsteps to\b",
        r"\bhow to\b", r"\bexecuted tool\b", r"\baction chain\b"
    ]

    SEMANTIC_KEYWORDS = [
        r"\bis defined as\b", r"\bmeans\b", r"\bcreator of\b", r"\bfact\b",
        r"\bdefinition\b", r"\bconcept\b", r"\bcreated by\b"
    ]

    @classmethod
    def classify(cls, observation: RawObservation) -> Tuple[MemoryType, MemoryMetadata]:
        content_lower = observation.content.lower()
        source = observation.source.lower()
        
        assigned_type = MemoryType.EPISODIC
        importance = 5.0
        retention = RetentionPolicy.EPISODIC
        extracted_tags = list(observation.tags)

        # 1. Preference Classification
        if any(re.search(pat, content_lower) for pat in cls.PREFERENCE_KEYWORDS):
            assigned_type = MemoryType.PREFERENCE
            importance = 8.5
            retention = RetentionPolicy.PERMANENT
            extracted_tags.append("preference")

        # 2. Project Classification
        elif source == "file" or any(re.search(pat, content_lower) for pat in cls.PROJECT_KEYWORDS):
            assigned_type = MemoryType.PROJECT
            importance = 7.0
            retention = RetentionPolicy.EPISODIC
            extracted_tags.append("project")

        # 3. Procedural Classification
        elif source == "tool_execution" or any(re.search(pat, content_lower) for pat in cls.PROCEDURAL_KEYWORDS):
            assigned_type = MemoryType.PROCEDURAL
            importance = 6.5
            retention = RetentionPolicy.EPISODIC
            extracted_tags.append("procedural")

        # 4. Semantic Classification
        elif any(re.search(pat, content_lower) for pat in cls.SEMANTIC_KEYWORDS):
            assigned_type = MemoryType.SEMANTIC
            importance = 7.5
            retention = RetentionPolicy.PERMANENT
            extracted_tags.append("semantic")

        # 5. Episodic Classification (Default)
        else:
            assigned_type = MemoryType.EPISODIC
            if source == "vision":
                importance = 4.0
                retention = RetentionPolicy.TRANSIENT
            elif source == "desktop_event":
                importance = 3.5
                retention = RetentionPolicy.TRANSIENT

        metadata = MemoryMetadata(
            importance_score=importance,
            confidence=1.0,
            source=source,
            retention_policy=retention,
            tags=list(set(extracted_tags))
        )

        return assigned_type, metadata
