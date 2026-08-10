"""
J.A.R.V.I.S. Intelligence I2.2 V5 — Deep Web Research & Source Discovery Package.
"""

from intelligence.web.deep_research.models import (
    EvidenceGapType,
    EvidenceGap,
    LinkCategory,
    LinkRejectionReason,
    DiscoveredLink,
    StoppingReason,
    QuestionCoverageState,
    QuestionCoverage,
    ResearchNoveltyDelta,
    DeepResearchConfig,
    DeepResearchFinding,
    DeepResearchRequest,
    DeepResearchResponse
)
from intelligence.web.deep_research.deep_research_service import web_deep_research_service

__all__ = [
    "EvidenceGapType",
    "EvidenceGap",
    "LinkCategory",
    "LinkRejectionReason",
    "DiscoveredLink",
    "StoppingReason",
    "QuestionCoverageState",
    "QuestionCoverage",
    "ResearchNoveltyDelta",
    "DeepResearchConfig",
    "DeepResearchFinding",
    "DeepResearchRequest",
    "DeepResearchResponse",
    "web_deep_research_service"
]
