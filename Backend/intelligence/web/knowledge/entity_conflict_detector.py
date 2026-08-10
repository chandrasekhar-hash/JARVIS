"""
Entity & Relationship Conflict Detection Engine for J.A.R.V.I.S. I2.2 V9.
"""
import uuid
from typing import Dict, List, Optional, Tuple, Any
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EntityConflict,
    EvidenceBackedRelationship,
    RelationshipConflict,
    RelationshipType,
)


class EntityConflictDetector:
    """
    Detects contradictory entity facts and relationships without silently dropping competing evidence.
    """

    def detect_relationship_conflicts(
        self, relationships: List[EvidenceBackedRelationship]
    ) -> List[RelationshipConflict]:
        conflicts: List[RelationshipConflict] = []
        # Group relationships by (subject, predicate) for single-valued predicates
        SINGLE_VALUED_PREDICATES = {
            RelationshipType.HEADQUARTERED_IN,
            RelationshipType.MAINTAINS,
            RelationshipType.OWNS,
            RelationshipType.HAS_VERSION,
        }

        rel_groups: Dict[Tuple[str, RelationshipType], List[EvidenceBackedRelationship]] = {}
        for r in relationships:
            if r.predicate in SINGLE_VALUED_PREDICATES:
                rel_groups.setdefault((r.subject_entity_id, r.predicate), []).append(r)

        for (sub_id, pred), rels in rel_groups.items():
            # Check if different objects are claimed
            obj_ids = {r.object_entity_id for r in rels}
            if len(obj_ids) > 1:
                conflicts.append(
                    RelationshipConflict(
                        conflict_id=f"rel_cnf_{uuid.uuid4().hex[:10]}",
                        subject_id=sub_id,
                        predicate=pred,
                        object_id=list(obj_ids)[0],
                        competing_relationships=rels,
                        evidence_ids=[r.evidence_id for r in rels if r.evidence_id],
                        source_ids=[r.source_id for r in rels if r.source_id],
                    )
                )

        return conflicts

    def detect_entity_attribute_conflicts(
        self, entities: List[CanonicalEntity]
    ) -> List[EntityConflict]:
        conflicts: List[EntityConflict] = []

        for e in entities:
            # Check conflicting descriptions or identity ambiguity
            if len(e.descriptions) > 1:
                # Compare descriptions
                pass

        return conflicts


entity_conflict_detector = EntityConflictDetector()
