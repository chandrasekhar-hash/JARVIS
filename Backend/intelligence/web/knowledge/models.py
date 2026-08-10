"""
Structured Entity, Relationship and Knowledge Models for J.A.R.V.I.S. I2.2 V9.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    COMPANY = "COMPANY"
    PRODUCT = "PRODUCT"
    SOFTWARE = "SOFTWARE"
    LIBRARY = "LIBRARY"
    TECHNOLOGY = "TECHNOLOGY"
    PROJECT = "PROJECT"
    PLACE = "PLACE"
    COUNTRY = "COUNTRY"
    CITY = "CITY"
    EVENT = "EVENT"
    DOCUMENT = "DOCUMENT"
    DATASET = "DATASET"
    WEB_RESOURCE = "WEB_RESOURCE"
    VERSION = "VERSION"
    STANDARD = "STANDARD"
    REGULATION = "REGULATION"
    CONCEPT = "CONCEPT"
    UNKNOWN = "UNKNOWN"


class EntityResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    PROBABLE = "PROBABLE"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    CONFLICTING = "CONFLICTING"


class RelationshipType(str, Enum):
    DEVELOPS = "DEVELOPS"
    MAINTAINS = "MAINTAINS"
    OWNS = "OWNS"
    CREATED_BY = "CREATED_BY"
    USED_BY = "USED_BY"
    DEPENDS_ON = "DEPENDS_ON"
    BUILT_WITH = "BUILT_WITH"
    PART_OF = "PART_OF"
    MEMBER_OF = "MEMBER_OF"
    LOCATED_IN = "LOCATED_IN"
    HEADQUARTERED_IN = "HEADQUARTERED_IN"
    ANNOUNCED = "ANNOUNCED"
    RELEASED = "RELEASED"
    HAS_VERSION = "HAS_VERSION"
    SUPERSEDES = "SUPERSEDES"
    REPLACES = "REPLACES"
    COMPATIBLE_WITH = "COMPATIBLE_WITH"
    INCOMPATIBLE_WITH = "INCOMPATIBLE_WITH"
    RELATED_TO = "RELATED_TO"
    CITES = "CITES"
    REFERENCES = "REFERENCES"
    DOCUMENTS = "DOCUMENTS"
    PUBLISHED_BY = "PUBLISHED_BY"
    ATTENDED_BY = "ATTENDED_BY"
    PARTICIPATES_IN = "PARTICIPATES_IN"
    FUNDED_BY = "FUNDED_BY"
    ACQUIRED_BY = "ACQUIRED_BY"
    FORK_OF = "FORK_OF"
    DERIVED_FROM = "DERIVED_FROM"
    HAS_RESOURCE = "HAS_RESOURCE"
    HAS_EVENT = "HAS_EVENT"
    HAS_PRODUCT = "HAS_PRODUCT"
    HAS_STANDARD = "HAS_STANDARD"
    UNKNOWN = "UNKNOWN"


class ProvenanceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REPAIRED = "REPAIRED"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"
    FORGED = "FORGED"


class KnowledgeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    AMBIGUOUS = "AMBIGUOUS"
    NO_EVIDENCE = "NO_EVIDENCE"
    ERROR = "ERROR"


@dataclass
class TemporalMetadata:
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    observed_at: Optional[str] = None
    published_at: Optional[str] = None
    event_time: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "observed_at": self.observed_at,
            "published_at": self.published_at,
            "event_time": self.event_time,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "TemporalMetadata":
        if not d:
            return cls()
        return cls(**d)


@dataclass
class EntityMention:
    mention_id: str
    surface_text: str
    normalized_text: str
    entity_type: EntityType
    source_id: str
    canonical_url: Optional[str] = None
    source_path: Optional[str] = None
    surrounding_context: Optional[str] = None
    evidence_id: Optional[str] = None
    temporal_metadata: Optional[TemporalMetadata] = None
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mention_id": self.mention_id,
            "surface_text": self.surface_text,
            "normalized_text": self.normalized_text,
            "entity_type": self.entity_type.value,
            "source_id": self.source_id,
            "canonical_url": self.canonical_url,
            "source_path": self.source_path,
            "surrounding_context": self.surrounding_context,
            "evidence_id": self.evidence_id,
            "temporal_metadata": self.temporal_metadata.to_dict() if self.temporal_metadata else None,
            "provenance_status": self.provenance_status.value,
        }


@dataclass
class CanonicalEntity:
    entity_id: str
    canonical_name: str
    entity_type: EntityType
    aliases: List[str] = field(default_factory=list)
    descriptions: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    canonical_urls: List[str] = field(default_factory=list)
    mention_ids: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    temporal_state: Optional[TemporalMetadata] = None
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    resolution_status: EntityResolutionStatus = EntityResolutionStatus.UNRESOLVED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type.value,
            "aliases": self.aliases,
            "descriptions": self.descriptions,
            "source_ids": self.source_ids,
            "canonical_urls": self.canonical_urls,
            "mention_ids": self.mention_ids,
            "evidence_ids": self.evidence_ids,
            "temporal_state": self.temporal_state.to_dict() if self.temporal_state else None,
            "provenance_status": self.provenance_status.value,
            "resolution_status": self.resolution_status.value,
        }


@dataclass
class EvidenceBackedRelationship:
    relationship_id: str
    subject_entity_id: str
    predicate: RelationshipType
    object_entity_id: str
    source_id: str
    canonical_url: Optional[str] = None
    source_path: Optional[str] = None
    evidence_id: Optional[str] = None
    temporal_metadata: Optional[TemporalMetadata] = None
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    extraction_method: str = "PROSE_HEURISTIC"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "subject_entity_id": self.subject_entity_id,
            "predicate": self.predicate.value,
            "object_entity_id": self.object_entity_id,
            "source_id": self.source_id,
            "canonical_url": self.canonical_url,
            "source_path": self.source_path,
            "evidence_id": self.evidence_id,
            "temporal_metadata": self.temporal_metadata.to_dict() if self.temporal_metadata else None,
            "provenance_status": self.provenance_status.value,
            "extraction_method": self.extraction_method,
        }


@dataclass
class EntityConflict:
    conflict_id: str
    entity_id: str
    conflict_type: str
    description: str
    competing_claims: List[Dict[str, Any]] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    temporal_context: Optional[TemporalMetadata] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "entity_id": self.entity_id,
            "conflict_type": self.conflict_type,
            "description": self.description,
            "competing_claims": self.competing_claims,
            "evidence_ids": self.evidence_ids,
            "source_ids": self.source_ids,
            "temporal_context": self.temporal_context.to_dict() if self.temporal_context else None,
        }


@dataclass
class RelationshipConflict:
    conflict_id: str
    subject_id: str
    predicate: RelationshipType
    object_id: str
    competing_relationships: List[EvidenceBackedRelationship] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "subject_id": self.subject_id,
            "predicate": self.predicate.value,
            "object_id": self.object_id,
            "competing_relationships": [r.to_dict() for r in self.competing_relationships],
            "evidence_ids": self.evidence_ids,
            "source_ids": self.source_ids,
        }


@dataclass
class KnowledgeGraphStats:
    total_entities: int = 0
    total_relationships: int = 0
    total_mentions: int = 0
    total_conflicts: int = 0
    traversal_depth: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships,
            "total_mentions": self.total_mentions,
            "total_conflicts": self.total_conflicts,
            "traversal_depth": self.traversal_depth,
        }


@dataclass
class KnowledgeWebRequest:
    query: str
    urls: List[str] = field(default_factory=list)
    conversation_id: Optional[str] = None
    owner_scope_id: Optional[str] = None
    max_depth: int = 2
    user_timezone: Optional[str] = None
    force_refresh: bool = False


@dataclass
class KnowledgeWebResponse:
    status: KnowledgeStatus
    entities: List[CanonicalEntity] = field(default_factory=list)
    relationships: List[EvidenceBackedRelationship] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    temporal_state: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    serialized_context: str = ""
    graph_statistics: KnowledgeGraphStats = field(default_factory=KnowledgeGraphStats)
    warnings: List[str] = field(default_factory=list)
    is_truncated: bool = False
    grounding_status: str = "NONE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "conflicts": self.conflicts,
            "temporal_state": self.temporal_state,
            "evidence": self.evidence,
            "provenance_status": self.provenance_status.value,
            "serialized_context": self.serialized_context,
            "graph_statistics": self.graph_statistics.to_dict(),
            "warnings": self.warnings,
            "is_truncated": self.is_truncated,
            "grounding_status": self.grounding_status,
        }
