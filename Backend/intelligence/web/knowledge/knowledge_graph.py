"""
Ephemeral, Bounded In-Memory Knowledge Graph Engine for J.A.R.V.I.S. I2.2 V9.
"""
from typing import Dict, List, Optional, Set, Tuple
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EntityType,
    EvidenceBackedRelationship,
    KnowledgeGraphStats,
    RelationshipType,
)


class ServerHardLimits:
    MAX_ENTITIES_PER_REQUEST = 200
    MAX_MENTIONS_PER_ENTITY = 50
    MAX_RELATIONSHIPS_PER_REQUEST = 300
    MAX_GRAPH_DEPTH = 4
    MAX_GRAPH_NODES = 250
    MAX_GRAPH_EDGES = 500
    MAX_ALIASES_PER_ENTITY = 50
    MAX_EVIDENCE_PER_ENTITY = 50
    MAX_KNOWLEDGE_CONTEXT_CHARS = 15000
    MAX_WALL_CLOCK_SECONDS = 20.0


class BoundedKnowledgeGraph:
    """
    In-memory, ephemeral, bounded graph data structure.
    Strictly enforces capacity limits to prevent uncontrolled memory growth.
    """

    def __init__(self):
        self._nodes: Dict[str, CanonicalEntity] = {}  # entity_id -> CanonicalEntity
        self._edges: Dict[str, EvidenceBackedRelationship] = {}  # rel_id -> Relationship
        self._adjacency_out: Dict[str, Set[str]] = {}  # sub_id -> set of rel_ids
        self._adjacency_in: Dict[str, Set[str]] = {}  # obj_id -> set of rel_ids
        self._is_truncated = False

    def add_entity(self, entity: CanonicalEntity) -> bool:
        if len(self._nodes) >= ServerHardLimits.MAX_GRAPH_NODES:
            self._is_truncated = True
            return False

        # Apply entity internal bounds
        if len(entity.aliases) > ServerHardLimits.MAX_ALIASES_PER_ENTITY:
            entity.aliases = entity.aliases[: ServerHardLimits.MAX_ALIASES_PER_ENTITY]
        if len(entity.evidence_ids) > ServerHardLimits.MAX_EVIDENCE_PER_ENTITY:
            entity.evidence_ids = entity.evidence_ids[: ServerHardLimits.MAX_EVIDENCE_PER_ENTITY]
        if len(entity.mention_ids) > ServerHardLimits.MAX_MENTIONS_PER_ENTITY:
            entity.mention_ids = entity.mention_ids[: ServerHardLimits.MAX_MENTIONS_PER_ENTITY]

        self._nodes[entity.entity_id] = entity
        self._adjacency_out.setdefault(entity.entity_id, set())
        self._adjacency_in.setdefault(entity.entity_id, set())
        return True

    def add_relationship(self, rel: EvidenceBackedRelationship) -> bool:
        if len(self._edges) >= ServerHardLimits.MAX_GRAPH_EDGES:
            self._is_truncated = True
            return False

        if rel.subject_entity_id not in self._nodes or rel.object_entity_id not in self._nodes:
            return False

        self._edges[rel.relationship_id] = rel
        self._adjacency_out.setdefault(rel.subject_entity_id, set()).add(rel.relationship_id)
        self._adjacency_in.setdefault(rel.object_entity_id, set()).add(rel.relationship_id)
        return True

    def get_entity(self, entity_id: str) -> Optional[CanonicalEntity]:
        return self._nodes.get(entity_id)

    def get_relationship(self, rel_id: str) -> Optional[EvidenceBackedRelationship]:
        return self._edges.get(rel_id)

    def get_outgoing_relationships(
        self, entity_id: str, predicate_filter: Optional[RelationshipType] = None
    ) -> List[EvidenceBackedRelationship]:
        rel_ids = self._adjacency_out.get(entity_id, set())
        results = []
        for rid in rel_ids:
            rel = self._edges.get(rid)
            if rel:
                if predicate_filter is None or rel.predicate == predicate_filter:
                    results.append(rel)
        return results

    def get_incoming_relationships(
        self, entity_id: str, predicate_filter: Optional[RelationshipType] = None
    ) -> List[EvidenceBackedRelationship]:
        rel_ids = self._adjacency_in.get(entity_id, set())
        results = []
        for rid in rel_ids:
            rel = self._edges.get(rid)
            if rel:
                if predicate_filter is None or rel.predicate == predicate_filter:
                    results.append(rel)
        return results

    def filter_entities_by_type(self, entity_type: EntityType) -> List[CanonicalEntity]:
        return [e for e in self._nodes.values() if e.entity_type == entity_type]

    def get_all_entities(self) -> List[CanonicalEntity]:
        return list(self._nodes.values())

    def get_all_relationships(self) -> List[EvidenceBackedRelationship]:
        return list(self._edges.values())

    def get_stats(self) -> KnowledgeGraphStats:
        return KnowledgeGraphStats(
            total_entities=len(self._nodes),
            total_relationships=len(self._edges),
            total_mentions=sum(len(e.mention_ids) for e in self._nodes.values()),
            total_conflicts=0,
            traversal_depth=0,
        )

    @property
    def is_truncated(self) -> bool:
        return self._is_truncated

    def clear(self):
        self._nodes.clear()
        self._edges.clear()
        self._adjacency_out.clear()
        self._adjacency_in.clear()
        self._is_truncated = False
