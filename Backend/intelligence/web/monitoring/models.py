"""
J.A.R.V.I.S. Intelligence I2.2 V8 — Web Monitoring & Change Detection Models.
Defines data structures, enums, change classifications, significance levels, snapshots, and server bounds.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time


class MonitorTargetType(str, Enum):
    WEBPAGE = "WEBPAGE"
    DOCUMENTATION = "DOCUMENTATION"
    RELEASE_PAGE = "RELEASE_PAGE"
    NEWS_SOURCE = "NEWS_SOURCE"
    STRUCTURED_DATASET = "STRUCTURED_DATASET"
    PRICING = "PRICING"
    PRODUCT_SPECIFICATION = "PRODUCT_SPECIFICATION"
    EVENT_PAGE = "EVENT_PAGE"
    API_DOCUMENTATION = "API_DOCUMENTATION"
    DYNAMIC_PAGE = "DYNAMIC_PAGE"
    UNKNOWN = "UNKNOWN"


class SourceAvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    HTTP_ERROR = "HTTP_ERROR"
    ACCESS_DENIED = "ACCESS_DENIED"
    TIMEOUT = "TIMEOUT"
    REMOVED = "REMOVED"
    UNKNOWN = "UNKNOWN"


class ObservationCompleteness(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ChangeType(str, Enum):
    CONTENT_ADDED = "CONTENT_ADDED"
    CONTENT_REMOVED = "CONTENT_REMOVED"
    CONTENT_MODIFIED = "CONTENT_MODIFIED"
    STRUCTURE_CHANGED = "STRUCTURE_CHANGED"
    VALUE_CHANGED = "VALUE_CHANGED"
    DATE_CHANGED = "DATE_CHANGED"
    VERSION_CHANGED = "VERSION_CHANGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    PRICE_CHANGED = "PRICE_CHANGED"
    RESOURCE_ADDED = "RESOURCE_ADDED"
    RESOURCE_REMOVED = "RESOURCE_REMOVED"
    LINK_CHANGED = "LINK_CHANGED"
    CORRECTION = "CORRECTION"
    ROLLBACK = "ROLLBACK"
    SOURCE_REMOVED = "SOURCE_REMOVED"
    SOURCE_RESTORED = "SOURCE_RESTORED"
    COSMETIC_ONLY = "COSMETIC_ONLY"
    NO_CHANGE = "NO_CHANGE"
    UNKNOWN = "UNKNOWN"


class ChangeSignificance(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    COSMETIC = "COSMETIC"
    UNKNOWN = "UNKNOWN"


class MonitorBaselineStatus(str, Enum):
    NO_BASELINE = "NO_BASELINE"
    NO_CHANGE = "NO_CHANGE"
    CHANGED = "CHANGED"
    PARTIAL_COMPARISON = "PARTIAL_COMPARISON"
    BASELINE_EXPIRED = "BASELINE_EXPIRED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class SnapshotTombstone:
    target_id: str
    owner_scope_id: str
    conversation_id: str
    expired_at: float
    last_snapshot_id: str
    expiration_reason: str = "TTL_EXPIRED"


@dataclass
class MonitoringSnapshot:
    snapshot_id: str
    owner_scope_id: str
    conversation_id: str
    target_id: str
    canonical_url: str
    previous_snapshot_id: Optional[str] = None
    retrieved_at: str = ""
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    content_fingerprint: str = ""
    structural_fingerprint: str = ""
    selected_text_blocks: List[str] = field(default_factory=list)
    heading_fingerprints: List[str] = field(default_factory=list)
    structured_record_fingerprints: List[str] = field(default_factory=list)
    important_field_values: Dict[str, str] = field(default_factory=dict)
    source_availability: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    completeness: ObservationCompleteness = ObservationCompleteness.COMPLETE
    retrieval_method: str = "V2_STATIC"
    created_timestamp: float = field(default_factory=time.time)


@dataclass
class ChangeEvidence:
    evidence_id: str
    change_type: ChangeType
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    snippet_before: Optional[str] = None
    snippet_after: Optional[str] = None
    source_path: str = ""
    is_meaningful: bool = True


@dataclass
class ChangeFinding:
    finding_id: str
    target_id: str
    canonical_url: str
    baseline_snapshot_id: str
    current_snapshot_id: str
    change_type: ChangeType
    significance: ChangeSignificance
    summary: str
    evidences: List[ChangeEvidence] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    provenance_status: str = "VALID"


@dataclass
class MonitorWebRequest:
    query: str
    url: Optional[str] = None
    conversation_id: Optional[str] = None
    owner_scope_id: Optional[str] = None
    target_type: MonitorTargetType = MonitorTargetType.WEBPAGE
    force_refresh: bool = False
    user_timezone: Optional[str] = None


@dataclass
class MonitorWebResponse:
    baseline_status: MonitorBaselineStatus
    query: str
    canonical_url: str = ""
    findings: List[ChangeFinding] = field(default_factory=list)
    serialized_context: str = ""
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


# Server Hard Configurations
class MonitoringConfig:
    MAX_MONITORED_TARGETS_PER_CONVERSATION: int = 10
    MAX_SNAPSHOTS_PER_TARGET: int = 5
    SNAPSHOT_TTL_SECONDS: int = 3600
    MAX_CHANGE_EVIDENCE_ITEMS: int = 50
    MAX_CHANGED_TEXT_CHARS: int = 12_000
    MAX_MONITOR_CONTEXT_CHARS: int = 15_000
    MAX_COMPARISON_PAGES: int = 5
    MAX_DYNAMIC_ESCALATIONS: int = 2
    MAX_MONITOR_RUNTIME_SECONDS: float = 20.0
    MAX_CONCURRENT_MONITOR_OPERATIONS: int = 4
