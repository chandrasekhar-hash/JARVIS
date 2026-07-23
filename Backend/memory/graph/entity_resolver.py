import re
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple
from memory.models.graph import KnowledgeNode


class EntityResolver:
    """
    Deterministic rule-based entity resolver extracting entity nodes (Person, Project,
    Application, File, Topic, Organization) from text payloads and observations.
    """

    # Keyword patterns mapped to entity types
    PERSON_PATTERNS = [
        r"\bchandrasekhar\b", r"\buser\b", r"\bdeveloper\b", r"\badmin\b", r"\bcreator\b"
    ]

    PROJECT_PATTERNS = [
        r"\bjarvis\b", r"\bbackend\b", r"\bfrontend\b", r"\bcodebase\b", r"\bworkspace\b"
    ]

    APP_PATTERNS = [
        r"\bvs code\b", r"\bvisual studio code\b", r"\bchrome\b", r"\bterminal\b",
        r"\bnotepad\b", r"\bspotify\b", r"\bexplorer\b"
    ]

    FILE_PATTERNS = [
        r"[\w\-\\./]+\.(?:py|js|rs|json|md|html|css|toml)\b"
    ]

    ORGANIZATION_PATTERNS = [
        r"\bgoogle\b", r"\bgithub\b", r"\bopenai\b", r"\banthropic\b"
    ]

    TOPIC_PATTERNS = [
        r"\bpython\b", r"\rust\b", r"\btauri\b", r"\bmemory\b", r"\bvision\b",
        r"\bdark mode\b", r"\btts\b", r"\bstorage\b"
    ]

    @staticmethod
    def normalize_label(label: str) -> str:
        """Normalizes entity label for canonical deduplication."""
        clean = label.strip().lower()
        clean = re.sub(r"[^\w\s\.-]", "", clean)
        return clean.title()

    @classmethod
    def extract_entities(cls, text: str, source_metadata: Optional[Dict[str, Any]] = None) -> List[KnowledgeNode]:
        """
        Extracts entity nodes from text strictly using deterministic pattern matching.
        """
        nodes: List[KnowledgeNode] = []
        seen_keys = set()
        text_lower = text.lower()
        now = time.time()

        def add_entity(label: str, entity_type: str, props: Optional[Dict[str, Any]] = None):
            norm_label = cls.normalize_label(label)
            key = (norm_label.lower(), entity_type.lower())
            if key in seen_keys or len(norm_label) < 2:
                return
            seen_keys.add(key)

            # Stable node ID generation based on canonical label and type
            node_id = f"node_{entity_type.lower()}_{hash(key) & 0xffffffff:08x}"
            
            nodes.append(
                KnowledgeNode(
                    node_id=node_id,
                    label=norm_label,
                    type=entity_type,
                    properties=props or {"source": "deterministic_extraction"},
                    created_at=now
                )
            )

        # 1. Person Entities
        for pat in cls.PERSON_PATTERNS:
            matches = re.findall(pat, text_lower)
            for m in matches:
                add_entity(m, "Person")

        # 2. Project Entities
        for pat in cls.PROJECT_PATTERNS:
            matches = re.findall(pat, text_lower)
            for m in matches:
                add_entity(m, "Project")

        # 3. Application Entities
        for pat in cls.APP_PATTERNS:
            matches = re.findall(pat, text_lower)
            for m in matches:
                add_entity(m, "Application")

        # 4. File Entities
        for pat in cls.FILE_PATTERNS:
            matches = re.findall(pat, text_lower)
            for m in matches:
                add_entity(m, "File")

        # 5. Organization Entities
        for pat in cls.ORGANIZATION_PATTERNS:
            matches = re.findall(pat, text_lower)
            for m in matches:
                add_entity(m, "Organization")

        # 6. Topic Entities
        for pat in cls.TOPIC_PATTERNS:
            matches = re.findall(pat, text_lower)
            for m in matches:
                add_entity(m, "Topic")

        return nodes
