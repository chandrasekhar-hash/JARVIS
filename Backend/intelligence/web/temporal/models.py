"""
Data models and enums for J.A.R.V.I.S. Intelligence I2.2 V4 — Current Events, News & Freshness Intelligence.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field
from intelligence.web.models import GroundingStatus


class TemporalIntent(str, Enum):
    """Supported Temporal Intent Categories."""
    LATEST = "LATEST"
    TODAY = "TODAY"
    YESTERDAY = "YESTERDAY"
    LAST_24_HOURS = "LAST_24_HOURS"
    THIS_WEEK = "THIS_WEEK"
    THIS_MONTH = "THIS_MONTH"
    SINCE_DATE = "SINCE_DATE"
    SINCE_LAST_CHECK = "SINCE_LAST_CHECK"
    BREAKING_NEWS = "BREAKING_NEWS"
    EVENT_TIMELINE = "EVENT_TIMELINE"
    UPDATE_TRACKING = "UPDATE_TRACKING"
    NEWS_SUMMARY = "NEWS_SUMMARY"
    CHANGE_DETECTION = "CHANGE_DETECTION"
    NON_TEMPORAL = "NON_TEMPORAL"


class TimePrecision(str, Enum):
    """Timestamp precision levels."""
    EXACT_DATETIME = "EXACT_DATETIME"
    DATE_ONLY = "DATE_ONLY"
    MONTH_ONLY = "MONTH_ONLY"
    YEAR_ONLY = "YEAR_ONLY"
    RELATIVE = "RELATIVE"
    UNKNOWN = "UNKNOWN"


class FreshnessCategory(str, Enum):
    """Categorical freshness states relative to query window."""
    CURRENT = "CURRENT"
    RECENT = "RECENT"
    STALE = "STALE"
    OUTSIDE_REQUESTED_WINDOW = "OUTSIDE_REQUESTED_WINDOW"
    UNKNOWN = "UNKNOWN"


class TimeSource(str, Enum):
    """Source provenance for timestamps."""
    STRUCTURED_METADATA = "STRUCTURED_METADATA"
    HTML_TIME_ELEMENT = "HTML_TIME_ELEMENT"
    OPEN_GRAPH = "OPEN_GRAPH"
    JSON_LD = "JSON_LD"
    SEARCH_PROVIDER = "SEARCH_PROVIDER"
    ARTICLE_TEXT = "ARTICLE_TEXT"
    OFFICIAL_ANNOUNCEMENT = "OFFICIAL_ANNOUNCEMENT"
    UNKNOWN = "UNKNOWN"


class UpdateCategory(str, Enum):
    """Categorical classification of story updates over time."""
    NEW_EVENT = "NEW_EVENT"
    NEW_DETAIL = "NEW_DETAIL"
    CORRECTION = "CORRECTION"
    OFFICIAL_CONFIRMATION = "OFFICIAL_CONFIRMATION"
    OFFICIAL_DENIAL = "OFFICIAL_DENIAL"
    STATUS_CHANGE = "STATUS_CHANGE"
    FOLLOW_UP = "FOLLOW_UP"
    REPEATED_INFORMATION = "REPEATED_INFORMATION"
    NO_MEANINGFUL_CHANGE = "NO_MEANINGFUL_CHANGE"


class TemporalDiffStatus(str, Enum):
    """Explicit diff status categories for since-last-check comparisons."""
    NEW = "NEW"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    REMOVED = "REMOVED"
    CORRECTED = "CORRECTED"
    UNKNOWN = "UNKNOWN"


class TemporalMetadata(BaseModel):
    """Comprehensive temporal provenance metadata."""
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    event_time: Optional[str] = None
    retrieved_at: str
    time_source: TimeSource = TimeSource.UNKNOWN
    time_precision: TimePrecision = TimePrecision.UNKNOWN
    freshness: FreshnessCategory = FreshnessCategory.UNKNOWN


class TemporalWindow(BaseModel):
    """Resolved time window normalized to UTC with explicit user timezone resolution state."""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    user_timezone: Optional[str] = None       # Resolution order: Explicit -> Session -> Unknown
    source_expression: str = ""
    is_relative: bool = True
    resolution_status: str = "RESOLVED"       # "RESOLVED", "UNCERTAIN_TIMEZONE", "INVALID_TIMEZONE"


class NewsEvent(BaseModel):
    """Structured news event extracted from evidence."""
    event_id: str
    title: str
    description: str
    event_time: Optional[str] = None
    first_published_at: Optional[str] = None
    latest_update_at: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    source_ids: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    update_category: UpdateCategory = UpdateCategory.NEW_EVENT
    temporal_metadata: TemporalMetadata


class StoryCluster(BaseModel):
    """Cluster of news reports describing the same underlying event."""
    cluster_id: str
    topic_title: str
    primary_source_id: Optional[str] = None
    member_source_ids: List[str] = Field(default_factory=list)
    events: List[NewsEvent] = Field(default_factory=list)
    is_old_news_resurfacing: bool = False
    resurfaced_original_date: Optional[str] = None


class TimelineEvent(BaseModel):
    """Sequential timeline entry with explicit timestamp precision."""
    timeline_id: str
    timestamp_str: str
    precision: TimePrecision
    summary: str
    source_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class TemporalClaim(BaseModel):
    """Factual claim with complete claim-to-temporal provenance linkage."""
    claim_id: str
    statement: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    temporal_metadata: TemporalMetadata


class TemporalSnapshot(BaseModel):
    """Ephemeral metadata-only snapshot for since-last-check tracking. Webpage bodies are NEVER stored."""
    snapshot_id: str
    conversation_id: str
    topic_fingerprint: str
    event_fingerprints: Set[str] = Field(default_factory=set)
    claim_fingerprints: Set[str] = Field(default_factory=set)
    canonical_urls: Set[str] = Field(default_factory=set)
    source_ids: Set[str] = Field(default_factory=set)
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    event_time: Optional[str] = None
    retrieved_at: str
    snapshot_created_at: float


class TemporalFinding(BaseModel):
    """Synthesized temporal research summary."""
    summary: str
    clusters: List[StoryCluster] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    claims: List[TemporalClaim] = Field(default_factory=list)
    diff_status: Optional[TemporalDiffStatus] = None
    has_prior_baseline: bool = True


class TemporalRequest(BaseModel):
    """API request model for temporal news research."""
    query: str
    user_timezone: Optional[str] = None        # MUST default to None; no silent UTC fallback
    force_temporal: bool = False
    conversation_id: Optional[str] = None


class TemporalResponse(BaseModel):
    """Complete temporal response payload."""
    query: str
    intent: TemporalIntent
    status: str  # "COMPLETE", "PARTIAL", "TIMEOUT", "FAILED"
    window: TemporalWindow
    clusters: List[StoryCluster] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    finding: Optional[TemporalFinding] = None
    grounding_status: GroundingStatus = GroundingStatus.FULL_PAGE_RETRIEVED
    latency_ms: float = 0.0
    error: Optional[str] = None
