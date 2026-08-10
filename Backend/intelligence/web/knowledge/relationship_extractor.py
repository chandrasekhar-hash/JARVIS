"""
Typed Relationship Extraction Engine for J.A.R.V.I.S. I2.2 V9.
"""
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EvidenceBackedRelationship,
    ProvenanceStatus,
    RelationshipType,
    TemporalMetadata,
)


class RelationshipExtractor:
    """
    Extracts typed, evidence-backed relationships between resolved canonical entities.
    """

    RELATIONSHIP_PATTERNS = [
        # (regex_pattern, RelationshipType, subject_group, object_group)
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:maintains|is maintained by)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.MAINTAINS, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:developed|develops|created|built)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.DEVELOPS, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:owns|acquired)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.OWNS, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:was acquired by)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.ACQUIRED_BY, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:depends on|uses)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.DEPENDS_ON, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:released|announced)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.RELEASED, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:is headquartered in|based in)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.HEADQUARTERED_IN, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+version\s+([vV]?\d+\.\d+(?:\.\d+)?)\b", RelationshipType.HAS_VERSION, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:supersedes|replaces)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.SUPERSEDES, 1, 2),
        (r"\b([A-Z][a-zA-Z0-9_\-\.]{1,30})\s+(?:is a fork of|forked from)\s+([A-Z][a-zA-Z0-9_\-\.]{1,30})\b", RelationshipType.FORK_OF, 1, 2),
    ]

    def extract_relationships_from_text(
        self,
        text: str,
        entities: List[CanonicalEntity],
        source_id: str,
        canonical_url: Optional[str] = None,
        source_path: Optional[str] = None,
        evidence_id: Optional[str] = None,
        temporal_metadata: Optional[TemporalMetadata] = None,
        provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED,
    ) -> List[EvidenceBackedRelationship]:
        if not text or len(entities) < 2:
            return []

        relationships: List[EvidenceBackedRelationship] = []
        entity_name_map = {e.canonical_name.lower(): e for e in entities}
        for e in entities:
            for alias in e.aliases:
                entity_name_map[alias.lower()] = e

        for pattern, predicate, sub_idx, obj_idx in self.RELATIONSHIP_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                raw_sub = match.group(sub_idx).strip()
                raw_obj = match.group(obj_idx).strip()

                sub_entity = entity_name_map.get(raw_sub.lower())
                obj_entity = entity_name_map.get(raw_obj.lower())

                # If object is a version string and predicate is HAS_VERSION
                if not obj_entity and predicate == RelationshipType.HAS_VERSION:
                    # Find or match version
                    for e in entities:
                        if e.canonical_name.lower() == raw_obj.lower():
                            obj_entity = e
                            break

                if sub_entity and obj_entity and sub_entity.entity_id != obj_entity.entity_id:
                    relationships.append(
                        EvidenceBackedRelationship(
                            relationship_id=f"rel_{uuid.uuid4().hex[:12]}",
                            subject_entity_id=sub_entity.entity_id,
                            predicate=predicate,
                            object_entity_id=obj_entity.entity_id,
                            source_id=source_id,
                            canonical_url=canonical_url,
                            source_path=source_path or "prose",
                            evidence_id=evidence_id,
                            temporal_metadata=temporal_metadata,
                            provenance_status=provenance_status,
                            extraction_method="PROSE_PATTERN",
                        )
                    )

        return relationships

    def extract_relationships_from_structured(
        self,
        structured_records: List[Dict[str, Any]],
        entities: List[CanonicalEntity],
        source_id: str,
        canonical_url: Optional[str] = None,
        provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED,
    ) -> List[EvidenceBackedRelationship]:
        relationships: List[EvidenceBackedRelationship] = []
        entity_name_map = {e.canonical_name.lower(): e for e in entities}

        for idx, rec in enumerate(structured_records):
            rec_data = rec.get("record_data") or rec
            subject_name = rec_data.get("subject") or rec_data.get("name") or rec_data.get("publisher")
            predicate_str = rec_data.get("predicate") or rec_data.get("relation") or rec_data.get("type")
            object_name = rec_data.get("object") or rec_data.get("target") or rec_data.get("author")

            if subject_name and object_name:
                sub_ent = entity_name_map.get(str(subject_name).lower())
                obj_ent = entity_name_map.get(str(object_name).lower())

                if sub_ent and obj_ent and sub_ent.entity_id != obj_ent.entity_id:
                    pred = self._map_predicate(str(predicate_str) if predicate_str else "")
                    relationships.append(
                        EvidenceBackedRelationship(
                            relationship_id=f"rel_st_{uuid.uuid4().hex[:12]}",
                            subject_entity_id=sub_ent.entity_id,
                            predicate=pred,
                            object_entity_id=obj_ent.entity_id,
                            source_id=source_id,
                            canonical_url=canonical_url or rec_data.get("url"),
                            source_path=f"structured[{idx}]",
                            evidence_id=rec.get("record_id") or rec.get("evidence_id"),
                            provenance_status=provenance_status,
                            extraction_method="STRUCTURED_RECORD",
                        )
                    )

        return relationships

    def _map_predicate(self, predicate_str: str) -> RelationshipType:
        p = predicate_str.upper()
        if "MAINTAIN" in p:
            return RelationshipType.MAINTAINS
        if "DEVELOP" in p or "AUTHOR" in p or "CREATOR" in p:
            return RelationshipType.DEVELOPS
        if "OWN" in p:
            return RelationshipType.OWNS
        if "ACQUIRE" in p:
            return RelationshipType.ACQUIRED_BY
        if "DEPEND" in p or "USE" in p:
            return RelationshipType.DEPENDS_ON
        if "VERSION" in p or "RELEASE" in p:
            return RelationshipType.HAS_VERSION
        if "FORK" in p:
            return RelationshipType.FORK_OF

        return RelationshipType.RELATED_TO


relationship_extractor = RelationshipExtractor()
