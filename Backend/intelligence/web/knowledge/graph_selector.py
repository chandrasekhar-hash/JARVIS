"""
Query-Aware Graph Selection & Explainable Ranking for J.A.R.V.I.S. I2.2 V9.
"""
from typing import Dict, List, Optional, Tuple
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EntityType,
    EvidenceBackedRelationship,
    ProvenanceStatus,
    RelationshipType,
)
from intelligence.web.knowledge.knowledge_graph import BoundedKnowledgeGraph, ServerHardLimits
from intelligence.web.knowledge.graph_traversal import graph_traversal_engine


class GraphSelector:
    """
    Selects and ranks the most relevant entities and relationships for a target user query.
    Uses deterministic lexical, topological, and provenance signals without arbitrary numeric scores.
    """

    def select_subgraph(
        self,
        graph: BoundedKnowledgeGraph,
        query: str,
        max_depth: int = 2,
    ) -> Tuple[List[CanonicalEntity], List[EvidenceBackedRelationship]]:
        all_entities = graph.get_all_entities()
        if not all_entities:
            return [], []

        query_terms = set(query.lower().split())

        # 1. Identify seed entity IDs based on lexical relevance
        seed_entity_ids: List[str] = []
        for entity in all_entities:
            name_terms = set(entity.canonical_name.lower().split())
            alias_terms = set(" ".join(entity.aliases).lower().split())
            if query_terms.intersection(name_terms) or query_terms.intersection(alias_terms):
                seed_entity_ids.append(entity.entity_id)

        # Fallback to all entities if no direct lexical match
        if not seed_entity_ids:
            seed_entity_ids = [e.entity_id for e in all_entities[:10]]

        # 2. Execute bounded graph traversal starting from seed entities
        sub_entities, sub_relationships = graph_traversal_engine.traverse(
            graph=graph,
            start_entity_ids=seed_entity_ids,
            max_depth=max_depth,
        )

        # 3. Deterministic sorting (Explainable ranking)
        def entity_rank_key(e: CanonicalEntity) -> Tuple[int, int, int]:
            # Priority: Provenance Verified (1), Num mentions (desc), Name
            prov_pri = 1 if e.provenance_status == ProvenanceStatus.VERIFIED else 0
            return (prov_pri, len(e.mention_ids), -len(e.canonical_name))

        def rel_rank_key(r: EvidenceBackedRelationship) -> Tuple[int, int]:
            prov_pri = 1 if r.provenance_status == ProvenanceStatus.VERIFIED else 0
            return (prov_pri, -len(r.relationship_id))

        sub_entities.sort(key=entity_rank_key, reverse=True)
        sub_relationships.sort(key=rel_rank_key, reverse=True)

        return (
            sub_entities[: ServerHardLimits.MAX_GRAPH_NODES],
            sub_relationships[: ServerHardLimits.MAX_GRAPH_EDGES],
        )


graph_selector = GraphSelector()
