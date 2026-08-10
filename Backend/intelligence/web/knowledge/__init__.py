"""
J.A.R.V.I.S. Intelligence I2.2 V9 — Web Entity, Relationship & Knowledge Intelligence Package.
"""
from intelligence.web.knowledge.models import (
    KnowledgeWebRequest,
    KnowledgeWebResponse,
    KnowledgeStatus,
    EntityType,
    RelationshipType,
    ProvenanceStatus,
    CanonicalEntity,
    EvidenceBackedRelationship,
)
from intelligence.web.knowledge.knowledge_service import web_knowledge_service, WebKnowledgeService

__all__ = [
    "web_knowledge_service",
    "WebKnowledgeService",
    "KnowledgeWebRequest",
    "KnowledgeWebResponse",
    "KnowledgeStatus",
    "EntityType",
    "RelationshipType",
    "ProvenanceStatus",
    "CanonicalEntity",
    "EvidenceBackedRelationship",
]
