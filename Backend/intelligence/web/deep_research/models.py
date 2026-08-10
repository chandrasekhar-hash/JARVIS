"""
Data models, enums, and configurations for J.A.R.V.I.S. Intelligence I2.2 V5 — Deep Web Research & Source Discovery.
"""

from enum import Enum
from typing import List, Optional, Set, Dict, Any
from pydantic import BaseModel, Field
from intelligence.web.models import GroundingStatus


class EvidenceGapType(str, Enum):
    """Categorical types of evidence gaps."""
    MISSING_PRIMARY_SOURCE = "MISSING_PRIMARY_SOURCE"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    ONLY_ONE_INDEPENDENT_SOURCE = "ONLY_ONE_INDEPENDENT_SOURCE"
    UNRESOLVED_CONTRADICTION = "UNRESOLVED_CONTRADICTION"
    MISSING_CURRENT_INFO = "MISSING_CURRENT_INFO"
    MISSING_HISTORICAL_CONTEXT = "MISSING_HISTORICAL_CONTEXT"
    MISSING_COMPARISON_SIDE = "MISSING_COMPARISON_SIDE"
    INSUFFICIENT_DOCUMENTATION = "INSUFFICIENT_DOCUMENTATION"
    MISSING_DATE_VERIFICATION = "MISSING_DATE_VERIFICATION"


class EvidenceGap(BaseModel):
    """Structurally represents an evidence gap."""
    gap_id: str
    gap_type: EvidenceGapType
    target: str
    sub_question_id: str
    description: str
    is_resolved: bool = False


class LinkCategory(str, Enum):
    """Categories for extracted candidate webpage links."""
    OFFICIAL = "OFFICIAL"
    PRIMARY_SOURCE = "PRIMARY_SOURCE"
    DOCUMENTATION = "DOCUMENTATION"
    ACADEMIC = "ACADEMIC"
    NEWS = "NEWS"
    REFERENCE = "REFERENCE"
    RELATED = "RELATED"
    IRRELEVANT = "IRRELEVANT"
    UNSAFE = "UNSAFE"


class LinkRejectionReason(str, Enum):
    """Explicit rejection reasons for candidate links."""
    NONE = "NONE"
    SSRF_BLOCKED = "SSRF_BLOCKED"
    ALREADY_VISITED = "ALREADY_VISITED"
    IRRELEVANT_DOMAIN = "IRRELEVANT_DOMAIN"
    NON_HTTP_SCHEME = "NON_HTTP_SCHEME"
    IP_ENCODED = "IP_ENCODED"
    LOOPBACK_OR_PRIVATE = "LOOPBACK_OR_PRIVATE"


class DiscoveredLink(BaseModel):
    """Extracted link metadata with explicit safety and eligibility states."""
    url: str
    canonical_url: str
    anchor_text: str
    surrounding_text: str = ""
    source_page_url: str
    category: LinkCategory = LinkCategory.RELATED
    is_url_safe: bool = True
    is_eligible_for_selection: bool = True
    rejection_reason: LinkRejectionReason = LinkRejectionReason.NONE


class StoppingReason(str, Enum):
    """Structural stopping reasons for bounded deep research."""
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    NO_NEW_INFORMATION = "NO_NEW_INFORMATION"
    SOURCE_EXHAUSTION = "SOURCE_EXHAUSTION"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    TIMEOUT = "TIMEOUT"
    PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"


class QuestionCoverageState(str, Enum):
    """Sub-question coverage state derived from evidence relationships."""
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"
    NO_EVIDENCE = "NO_EVIDENCE"


class QuestionCoverage(BaseModel):
    """Structural coverage status per sub-question."""
    sub_question_id: str
    question_text: str
    coverage_state: QuestionCoverageState
    evidence_ids: List[str] = Field(default_factory=list)
    primary_sources: List[str] = Field(default_factory=list)


class ResearchNoveltyDelta(BaseModel):
    """Deterministic novelty tracking per research round."""
    round_index: int
    new_independent_sources_count: int = 0
    new_evidence_chunks_count: int = 0
    resolved_gaps_count: int = 0
    newly_discovered_conflicts_count: int = 0
    newly_verified_primary_sources_count: int = 0


class DeepResearchConfig(BaseModel):
    """Server-side hard limits for deep research."""
    max_rounds: int = 3
    max_search_queries_total: int = 8
    max_fetched_pages: int = 10
    max_discovered_links_per_page: int = 10
    max_selected_evidence_chunks: int = 12
    max_evidence_chars: int = 18000
    max_wall_clock_seconds: float = 30.0
    max_concurrent_fetches: int = 3


class DeepResearchFinding(BaseModel):
    """Synthesized deep research summary."""
    summary: str
    established_findings: List[str] = Field(default_factory=list)
    primary_source_statements: List[str] = Field(default_factory=list)
    independently_confirmed: List[str] = Field(default_factory=list)
    conflicting_evidence: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class DeepResearchRequest(BaseModel):
    """API request model for deep web research."""
    query: str
    conversation_id: Optional[str] = None
    user_timezone: Optional[str] = None
    max_rounds: int = 3
    force_deep_research: bool = False


class DeepResearchResponse(BaseModel):
    """Complete deep web research response payload."""
    query: str
    status: str  # "COMPLETE", "PARTIAL", "TIMEOUT", "FAILED"
    stopping_reason: StoppingReason
    finding: Optional[DeepResearchFinding] = None
    rounds_completed: int = 0
    total_queries: int = 0
    total_pages_fetched: int = 0
    urls_discovered: int = 0
    urls_rejected: int = 0
    gaps_resolved_count: int = 0
    primary_sources_count: int = 0
    contradictions_count: int = 0
    coverage: List[QuestionCoverage] = Field(default_factory=list)
    grounding_status: GroundingStatus = GroundingStatus.FULL_PAGE_RETRIEVED
    latency_ms: float = 0.0
    error: Optional[str] = None
