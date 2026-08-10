"""
Web Search Models for J.A.R.V.I.S. I2.2 V1 Web Search Foundation.
Defines intent categories, freshness statuses, search result schemas, requests, and responses.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WebSearchIntent(str, Enum):
    """Supported Web Search Intents."""
    GENERAL = "GENERAL"
    CURRENT_INFORMATION = "CURRENT_INFORMATION"
    NEWS = "NEWS"
    DOCUMENTATION = "DOCUMENTATION"
    OFFICIAL_SOURCE = "OFFICIAL_SOURCE"
    TECHNICAL = "TECHNICAL"
    ACADEMIC = "ACADEMIC"
    COMPARISON = "COMPARISON"
    FACT_CHECK = "FACT_CHECK"
    NAVIGATIONAL = "NAVIGATIONAL"


class FreshnessStatus(str, Enum):
    """Publication freshness status for retrieved items."""
    KNOWN_CURRENT = "KNOWN_CURRENT"
    KNOWN_OLD = "KNOWN_OLD"
    UNKNOWN = "UNKNOWN"


class SearchResultItem(BaseModel):
    """Normalized search result model with complete source provenance."""
    title: str
    url: str
    canonical_url: str
    domain: str
    snippet: str
    published_at: Optional[str] = None
    retrieved_at: str
    provider: str
    provider_rank: int
    source_type: str = "general"  # official, documentation, news, academic, general
    query_used: str = ""
    is_official_source: bool = False
    freshness_status: FreshnessStatus = FreshnessStatus.UNKNOWN
    relevance_score: float = 0.0  # Deterministic internal ranking score only
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class WebSearchRequest(BaseModel):
    """API and internal request model for web search."""
    query: str
    max_results: int = 10
    force_search: bool = False
    freshness_days: Optional[int] = None


class WebSearchResponse(BaseModel):
    """Complete web search response payload."""
    query: str
    web_needed: bool
    intent: WebSearchIntent
    planned_queries: List[str] = Field(default_factory=list)
    results: List[SearchResultItem] = Field(default_factory=list)
    total_results: int = 0
    retrieved_at: str
    provider: str
    latency_ms: float = 0.0
    freshness_applied: bool = False
    error: Optional[str] = None


# =====================================================================
# I2.2 V2 — WEBPAGE RETRIEVAL & CONTENT INTELLIGENCE MODELS
# =====================================================================

class WebPageBlockType(str, Enum):
    """Supported content block categories extracted from parsed web pages."""
    TITLE = "TITLE"
    HEADING = "HEADING"
    PARAGRAPH = "PARAGRAPH"
    LIST = "LIST"
    TABLE = "TABLE"
    CODE = "CODE"
    QUOTE = "QUOTE"
    OTHER = "OTHER"


class WebRetrievalStatus(str, Enum):
    """Execution status codes for webpage fetching and content extraction."""
    SUCCESS = "SUCCESS"
    SSRF_BLOCKED = "SSRF_BLOCKED"
    FETCH_FAILED = "FETCH_FAILED"
    TIMEOUT = "TIMEOUT"
    OVERSIZED = "OVERSIZED"
    UNSUPPORTED_CONTENT_TYPE = "UNSUPPORTED_CONTENT_TYPE"
    PDF_HANDOFF = "PDF_HANDOFF"
    JS_RENDER_REQUIRED = "JS_RENDER_REQUIRED"
    EMPTY_CONTENT = "EMPTY_CONTENT"
    HTTP_ERROR = "HTTP_ERROR"


class GroundingStatus(str, Enum):
    """Truthful grounding status states for JARVIS reasoning responses."""
    SEARCH_VERIFIED = "SEARCH_VERIFIED"
    FULL_PAGE_RETRIEVED = "FULL_PAGE_RETRIEVED"
    SEARCH_SNIPPET_FALLBACK = "SEARCH_SNIPPET_FALLBACK"


class WebPageRequest(BaseModel):
    """Request model for direct webpage fetch & extraction."""
    url: str
    query: Optional[str] = None
    max_content_chars: int = 50000
    timeout_seconds: float = 10.0
    allow_redirects: bool = True


class WebPageMetadata(BaseModel):
    """Strict metadata extracted from a retrieved webpage with complete source provenance."""
    requested_url: str
    final_url: str
    canonical_url: str
    domain: str
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    modified_at: Optional[str] = None
    content_type: str = "text/html"
    language: Optional[str] = None
    retrieved_at: str
    http_status: int = 200


class WebContentBlock(BaseModel):
    """Structured semantic block within an extracted webpage document."""
    block_index: int
    block_type: WebPageBlockType
    text: str
    heading_path: List[str] = Field(default_factory=list)
    source_url: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceChunk(BaseModel):
    """Bounded, query-scored evidence chunk preserving source provenance and heading context."""
    source_id: str
    source_url: str
    chunk_index: int
    heading_path: List[str] = Field(default_factory=list)
    block_range: List[int] = Field(default_factory=list)
    text: str
    relevance_score: float = 0.0


class EvidenceRegistry(BaseModel):
    """Backend source evidence registry mapping source IDs to verified canonical metadata."""
    sources: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # "source_1" -> {canonical_url, title, domain}


class WebPageDocument(BaseModel):
    """Extracted structured document representation of a fetched webpage."""
    metadata: WebPageMetadata
    blocks: List[WebContentBlock] = Field(default_factory=list)
    extracted_text: str = ""
    evidence_chunks: List[EvidenceChunk] = Field(default_factory=list)
    content_length: int = 0
    truncated: bool = False
    retrieval_status: WebRetrievalStatus = WebRetrievalStatus.SUCCESS
    warnings: List[str] = Field(default_factory=list)


class WebRetrievalResponse(BaseModel):
    """Response payload for webpage retrieval and content intelligence."""
    success: bool
    document: Optional[WebPageDocument] = None
    evidence_registry: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: float = 0.0

