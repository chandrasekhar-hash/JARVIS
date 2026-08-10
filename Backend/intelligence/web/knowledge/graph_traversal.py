"""
Bounded Graph Traversal Engine for J.A.R.V.I.S. I2.2 V9.
"""
from typing import Dict, List, Optional, Set, Tuple
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EntityType,
    EvidenceBackedRelationship,
    RelationshipType,
)
from intelligence.web.knowledge.knowledge_graph import BoundedKnowledgeGraph, ServerHardLimits


class GraphTraversalEngine:
    """
    Executes bounded, deterministic multi-hop graph traversal with strict cycle prevention.
    """

    def traverse(
        self,
        graph: BoundedKnowledgeGraph,
        start_entity_ids: List[str],
        max_depth: int = 2,
        relationship_types: Optional[List[RelationshipType]] = None,
        entity_types: Optional[List[EntityType]] = None,
    ) -> Tuple[List[CanonicalEntity], List[EvidenceBackedRelationship]]:
        # Enforce server depth ceiling
        effective_depth = min(max_depth, ServerHardLimits.MAX_GRAPH_DEPTH)

        visited_entity_ids: Set[str] = set()
        visited_rel_ids: Set[str] = set()

        result_entities: List[CanonicalEntity] = []
        result_relationships: List[EvidenceBackedRelationship] = []

        current_frontier: Set[str] = set(start_entity_ids)

        for depth in range(effective_depth + 1):
            if not current_frontier:
                break

            next_frontier: Set[str] = set()

            for entity_id in current_frontier:
                if entity_id in visited_entity_ids:
                    continue

                entity = graph.get_entity(entity_id)
                if not entity:
                    continue

                # Filter entity type if requested
                if entity_types and entity.entity_type not in entity_types:
                    continue

                visited_entity_ids.add(entity_id)
                result_entities.append(entity)

                # Stop expanding further if max_depth reached
                if depth == effective_depth:
                    continue

                # Get outgoing and incoming relationships
                outgoing = graph.get_outgoing_relationships(entity_id)
                incoming = graph.get_incoming_relationships(entity_id)

                all_rels = outgoing + incoming

                for rel in all_rels:
                    if rel.relationship_id in visited_rel_ids:
                        continue

                    # Predicate filter
                    if relationship_types and rel.predicate not in relationship_types:
                        continue

                    visited_rel_ids.add(rel.relationship_id)
                    result_relationships.append(rel)

                    # Determine neighbor entity ID
                    neighbor_id = (
                        rel.object_entity_id
                        if rel.subject_entity_id == entity_id
                        else rel.subject_entity_id
                    )

                    if neighbor_id not in visited_entity_ids:
                        next_frontier.add(neighbor_id)

            current_frontier = next_frontier

        return result_entities, result_relationships


graph_traversal_engine = GraphTraversalEngine()
