"""
Relationship Normalization & Direction Correctness for J.A.R.V.I.S. I2.2 V9.
"""
from typing import Dict, List, Optional
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EntityType,
    EvidenceBackedRelationship,
    RelationshipType,
)


class RelationshipNormalizer:
    """
    Normalizes relationships, enforces directional semantics, and filters invalid edges.
    """

    # Directives for expected entity types for subjects and objects
    PREDICATE_CONSTRAINTS = {
        RelationshipType.MAINTAINS: (
            {EntityType.ORGANIZATION, EntityType.COMPANY, EntityType.PERSON},
            {EntityType.SOFTWARE, EntityType.PROJECT, EntityType.LIBRARY, EntityType.PRODUCT, EntityType.TECHNOLOGY},
        ),
        RelationshipType.DEVELOPS: (
            {EntityType.ORGANIZATION, EntityType.COMPANY, EntityType.PERSON},
            {EntityType.SOFTWARE, EntityType.PROJECT, EntityType.LIBRARY, EntityType.PRODUCT, EntityType.TECHNOLOGY},
        ),
        RelationshipType.OWNS: (
            {EntityType.ORGANIZATION, EntityType.COMPANY, EntityType.PERSON},
            {EntityType.COMPANY, EntityType.PRODUCT, EntityType.SOFTWARE, EntityType.PROJECT, EntityType.WEB_RESOURCE},
        ),
        RelationshipType.HEADQUARTERED_IN: (
            {EntityType.ORGANIZATION, EntityType.COMPANY},
            {EntityType.CITY, EntityType.COUNTRY, EntityType.PLACE},
        ),
        RelationshipType.HAS_VERSION: (
            {EntityType.SOFTWARE, EntityType.PROJECT, EntityType.LIBRARY, EntityType.PRODUCT, EntityType.TECHNOLOGY, EntityType.STANDARD},
            {EntityType.VERSION, EntityType.CONCEPT, EntityType.UNKNOWN},
        ),
    }

    def normalize_relationship(
        self,
        rel: EvidenceBackedRelationship,
        entity_map: Dict[str, CanonicalEntity],
    ) -> Optional[EvidenceBackedRelationship]:
        if not rel.subject_entity_id or not rel.object_entity_id:
            return None

        sub_ent = entity_map.get(rel.subject_entity_id)
        obj_ent = entity_map.get(rel.object_entity_id)

        if not sub_ent or not obj_ent:
            return None

        # Prevent self-loop relationships
        if rel.subject_entity_id == rel.object_entity_id:
            return None

        # Direction check: If subject and object are reversed according to predicate constraints
        constraints = self.PREDICATE_CONSTRAINTS.get(rel.predicate)
        if constraints:
            allowed_sub_types, allowed_obj_types = constraints
            # Check if reversed (e.g. React MAINTAINS Meta instead of Meta MAINTAINS React)
            if (
                sub_ent.entity_type in allowed_obj_types
                and obj_ent.entity_type in allowed_sub_types
                and sub_ent.entity_type not in allowed_sub_types
            ):
                # Swap subject and object to fix direction
                rel.subject_entity_id, rel.object_entity_id = (
                    rel.object_entity_id,
                    rel.subject_entity_id,
                )

        return rel


relationship_normalizer = RelationshipNormalizer()
