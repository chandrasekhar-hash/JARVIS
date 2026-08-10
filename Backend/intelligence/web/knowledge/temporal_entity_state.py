"""
Temporal Entity & Relationship State Tracking for J.A.R.V.I.S. I2.2 V9.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EvidenceBackedRelationship,
    TemporalMetadata,
)


@dataclass
class TemporalStateRecord:
    state_id: str
    entity_or_rel_id: str
    attribute_name: str
    previous_value: Optional[str]
    current_value: str
    temporal_metadata: TemporalMetadata
    evidence_id: Optional[str] = None
    source_id: Optional[str] = None


class TemporalEntityStateTracker:
    """
    Manages temporal transitions and preserves historical evidence without overwriting past facts.
    """

    def __init__(self):
        self._history: Dict[str, List[TemporalStateRecord]] = {}

    def record_state_transition(
        self,
        entity_or_rel_id: str,
        attribute_name: str,
        previous_value: Optional[str],
        current_value: str,
        temporal_metadata: TemporalMetadata,
        evidence_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> TemporalStateRecord:
        state_id = f"ts_{len(self._history.get(entity_or_rel_id, [])) + 1}_{attribute_name}"
        record = TemporalStateRecord(
            state_id=state_id,
            entity_or_rel_id=entity_or_rel_id,
            attribute_name=attribute_name,
            previous_value=previous_value,
            current_value=current_value,
            temporal_metadata=temporal_metadata,
            evidence_id=evidence_id,
            source_id=source_id,
        )

        self._history.setdefault(entity_or_rel_id, []).append(record)
        return record

    def get_history_for_id(self, entity_or_rel_id: str) -> List[TemporalStateRecord]:
        return self._history.get(entity_or_rel_id, [])

    def clear(self):
        self._history.clear()


temporal_entity_state_tracker = TemporalEntityStateTracker()
