"""
Conservative Entity Resolution Engine for J.A.R.V.I.S. I2.2 V9.
"""
from typing import Dict, List, Optional, Tuple, Set
from intelligence.web.knowledge.models import (
    CanonicalEntity,
    EntityMention,
    EntityResolutionStatus,
    EntityType,
    ProvenanceStatus,
)
from intelligence.web.knowledge.entity_normalizer import entity_normalizer
from intelligence.web.knowledge.alias_resolver import alias_resolver


class EntityResolver:
    """
    Executes conservative cross-source entity resolution based on explicit evidence signals.
    No arbitrary numeric confidence scores are exposed.
    """

    def __init__(self):
        self._entities: Dict[str, CanonicalEntity] = {}
        # Indexes for fast lookup
        self._canonical_url_map: Dict[str, str] = {}  # url -> entity_id
        self._repo_pkg_map: Dict[str, str] = {}  # pkg/repo -> entity_id
        self._norm_name_type_map: Dict[Tuple[str, EntityType], str] = {}  # (norm_name, type) -> entity_id
        self._norm_name_multimap: Dict[str, List[str]] = {}  # norm_name -> List[entity_id]

    def reset(self):
        self._entities.clear()
        self._canonical_url_map.clear()
        self._repo_pkg_map.clear()
        self._norm_name_type_map.clear()
        self._norm_name_multimap.clear()

    def resolve_mention(
        self, mention: EntityMention
    ) -> Tuple[Optional[CanonicalEntity], EntityResolutionStatus]:
        """
        Resolves an EntityMention to an existing or new CanonicalEntity conservatively.
        """
        if not mention.normalized_text:
            return None, EntityResolutionStatus.UNRESOLVED

        # 1. Exact Canonical URL match (Strongest signal)
        if mention.canonical_url and mention.canonical_url in self._canonical_url_map:
            target_id = self._canonical_url_map[mention.canonical_url]
            entity = self._entities[target_id]
            # Check type mismatch
            if entity.entity_type != mention.entity_type and entity.entity_type != EntityType.UNKNOWN and mention.entity_type != EntityType.UNKNOWN:
                return entity, EntityResolutionStatus.CONFLICTING
            return entity, EntityResolutionStatus.RESOLVED

        # 2. Package / Repo identifier match
        pkg_key = self._extract_package_repo_key(mention)
        if pkg_key and pkg_key in self._repo_pkg_map:
            target_id = self._repo_pkg_map[pkg_key]
            entity = self._entities[target_id]
            if entity.entity_type != mention.entity_type and entity.entity_type != EntityType.UNKNOWN and mention.entity_type != EntityType.UNKNOWN:
                return entity, EntityResolutionStatus.CONFLICTING
            return entity, EntityResolutionStatus.RESOLVED

        # 3. Alias match
        alias_entity_ids = alias_resolver.resolve_alias_to_entity_ids(mention.normalized_text)
        if len(alias_entity_ids) == 1:
            target_id = alias_entity_ids[0]
            entity = self._entities.get(target_id)
            if entity:
                if entity.entity_type == mention.entity_type or entity.entity_type == EntityType.UNKNOWN or mention.entity_type == EntityType.UNKNOWN:
                    return entity, EntityResolutionStatus.PROBABLE
        elif len(alias_entity_ids) > 1:
            return None, EntityResolutionStatus.AMBIGUOUS

        # 4. Exact (normalized_name, entity_type) match
        type_key = (mention.normalized_text, mention.entity_type)
        if type_key in self._norm_name_type_map:
            target_id = self._norm_name_type_map[type_key]
            entity = self._entities[target_id]
            return entity, EntityResolutionStatus.RESOLVED

        # 5. Check if same normalized name exists under DIFFERENT entity types (Same-name different-entity protection)
        existing_ids = self._norm_name_multimap.get(mention.normalized_text, [])
        if existing_ids:
            types = {self._entities[eid].entity_type for eid in existing_ids if eid in self._entities}
            if mention.entity_type not in types and EntityType.UNKNOWN not in types and mention.entity_type != EntityType.UNKNOWN:
                # Same name, different type -> DO NOT merge! Return UNRESOLVED (will create new entity of different type)
                return None, EntityResolutionStatus.UNRESOLVED

        # 6. Fallback: UNRESOLVED
        return None, EntityResolutionStatus.UNRESOLVED

    def merge_or_create(
        self, mention: EntityMention
    ) -> Tuple[CanonicalEntity, EntityResolutionStatus]:
        existing_entity, status = self.resolve_mention(mention)

        if existing_entity and status in (EntityResolutionStatus.RESOLVED, EntityResolutionStatus.PROBABLE):
            # Merge mention into existing entity
            self._update_entity_with_mention(existing_entity, mention)
            return existing_entity, status

        if status == EntityResolutionStatus.CONFLICTING:
            # Keep separate or flag conflict
            new_entity = self._create_new_canonical_entity(mention, status=EntityResolutionStatus.CONFLICTING)
            return new_entity, EntityResolutionStatus.CONFLICTING

        if status == EntityResolutionStatus.AMBIGUOUS:
            new_entity = self._create_new_canonical_entity(mention, status=EntityResolutionStatus.AMBIGUOUS)
            return new_entity, EntityResolutionStatus.AMBIGUOUS

        # Create brand new CanonicalEntity
        new_entity = self._create_new_canonical_entity(mention, status=EntityResolutionStatus.RESOLVED)
        return new_entity, EntityResolutionStatus.RESOLVED

    def _create_new_canonical_entity(
        self, mention: EntityMention, status: EntityResolutionStatus
    ) -> CanonicalEntity:
        entity_id = f"ent_{len(self._entities) + 1}_{mention.normalized_text[:16]}"
        entity = CanonicalEntity(
            entity_id=entity_id,
            canonical_name=mention.surface_text,
            entity_type=mention.entity_type,
            aliases=[mention.surface_text] if mention.surface_text != mention.normalized_text else [],
            descriptions=[],
            source_ids=[mention.source_id] if mention.source_id else [],
            canonical_urls=[mention.canonical_url] if mention.canonical_url else [],
            mention_ids=[mention.mention_id],
            evidence_ids=[mention.evidence_id] if mention.evidence_id else [],
            temporal_state=mention.temporal_metadata,
            provenance_status=mention.provenance_status,
            resolution_status=status,
        )

        self._entities[entity_id] = entity

        # Indexing
        if mention.canonical_url:
            self._canonical_url_map[mention.canonical_url] = entity_id

        pkg_key = self._extract_package_repo_key(mention)
        if pkg_key:
            self._repo_pkg_map[pkg_key] = entity_id

        type_key = (mention.normalized_text, mention.entity_type)
        self._norm_name_type_map[type_key] = entity_id
        self._norm_name_multimap.setdefault(mention.normalized_text, []).append(entity_id)

        # Register default alias
        alias_resolver.register_alias(
            alias=mention.surface_text,
            normalized_alias=mention.normalized_text,
            canonical_entity_id=entity_id,
            source_id=mention.source_id,
            canonical_url=mention.canonical_url,
            evidence_id=mention.evidence_id,
            provenance_status=mention.provenance_status,
        )

        return entity

    def _update_entity_with_mention(self, entity: CanonicalEntity, mention: EntityMention):
        if mention.mention_id not in entity.mention_ids:
            entity.mention_ids.append(mention.mention_id)
        if mention.source_id and mention.source_id not in entity.source_ids:
            entity.source_ids.append(mention.source_id)
        if mention.canonical_url and mention.canonical_url not in entity.canonical_urls:
            entity.canonical_urls.append(mention.canonical_url)
            self._canonical_url_map[mention.canonical_url] = entity.entity_id
        if mention.evidence_id and mention.evidence_id not in entity.evidence_ids:
            entity.evidence_ids.append(mention.evidence_id)
        if mention.surface_text not in entity.aliases and mention.surface_text != entity.canonical_name:
            entity.aliases.append(mention.surface_text)

        # Update entity_type if UNKNOWN
        if entity.entity_type == EntityType.UNKNOWN and mention.entity_type != EntityType.UNKNOWN:
            entity.entity_type = mention.entity_type

    def _extract_package_repo_key(self, mention: EntityMention) -> Optional[str]:
        if not mention.canonical_url:
            return None
        url = mention.canonical_url.lower()
        if "github.com/" in url:
            parts = url.split("github.com/")[-1].strip("/").split("/")
            if len(parts) >= 2:
                return f"github:{parts[0]}/{parts[1]}"
        if "npmjs.com/package/" in url:
            pkg = url.split("npmjs.com/package/")[-1].strip("/")
            return f"npm:{pkg}"
        if "pypi.org/project/" in url:
            pkg = url.split("pypi.org/project/")[-1].strip("/")
            return f"pypi:{pkg}"
        return None

    def get_all_entities(self) -> List[CanonicalEntity]:
        return list(self._entities.values())

    def get_entity_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        return self._entities.get(entity_id)


entity_resolver = EntityResolver()
