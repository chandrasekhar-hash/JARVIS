"""
J.A.R.V.I.S. Intelligence I2.2 V3 — Multi-Source Research & Evidence Synthesis Package.
"""

from intelligence.web.research.models import (
    ResearchIntent,
    FactCheckStatus,
    EvidenceRelationship,
    ResearchStatus,
    SourceSuitability,
    ResearchQuestion,
    ResearchPlan,
    ResearchSource,
    EvidenceItem,
    ResearchClaim,
    FactCheckDetail,
    ResearchConflict,
    ResearchFinding,
    ResearchRequest,
    ResearchResponse
)
from intelligence.web.research.research_service import web_research_service

__all__ = [
    "ResearchIntent",
    "FactCheckStatus",
    "EvidenceRelationship",
    "ResearchStatus",
    "SourceSuitability",
    "ResearchQuestion",
    "ResearchPlan",
    "ResearchSource",
    "EvidenceItem",
    "ResearchClaim",
    "FactCheckDetail",
    "ResearchConflict",
    "ResearchFinding",
    "ResearchRequest",
    "ResearchResponse",
    "web_research_service"
]
