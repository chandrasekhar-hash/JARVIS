"""
J.A.R.V.I.S. Intelligence I2.2 V6 — Structured Data & Resource Models.
Defines data structures, enums, rejection reasons, and server bounds for structured web data.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time


class StructuredDataType(str, Enum):
    HTML_TABLE = "HTML_TABLE"
    JSON = "JSON"
    JSON_LD = "JSON_LD"
    RSS = "RSS"
    ATOM = "ATOM"
    STRUCTURED_LIST = "STRUCTURED_LIST"
    SPECIFICATION = "SPECIFICATION"
    RELEASE_DATA = "RELEASE_DATA"
    EVENT_DATA = "EVENT_DATA"
    DATASET = "DATASET"
    DOWNLOADABLE_RESOURCE = "DOWNLOADABLE_RESOURCE"
    PAGINATION = "PAGINATION"
    UNKNOWN = "UNKNOWN"


class LinkRejectionReason(str, Enum):
    NONE = "NONE"
    SSRF_BLOCKED = "SSRF_BLOCKED"
    LOOPBACK_OR_PRIVATE = "LOOPBACK_OR_PRIVATE"
    IP_ENCODED = "IP_ENCODED"
    ALREADY_VISITED = "ALREADY_VISITED"
    NON_HTTP_SCHEME = "NON_HTTP_SCHEME"
    MIME_MISMATCH = "MIME_MISMATCH"
    OVER_BUDGET = "OVER_BUDGET"


@dataclass
class StructuredField:
    name: str
    value: str  # Exact original string from source
    source_path: str  # Deterministic, reproducible path (e.g. table[0].tbody.row[3].cell[1])
    normalized_value: Optional[Any] = None  # Deterministic normalized representation (or None)
    unit: Optional[str] = None
    source_id: str = ""


@dataclass
class StructuredRecord:
    record_id: str
    record_type: StructuredDataType
    fields: List[StructuredField] = field(default_factory=list)
    source_id: str = ""
    canonical_url: str = ""
    extraction_method: str = ""
    schema_type: Optional[str] = None  # e.g. Product, SoftwareApplication, Article
    temporal_metadata: Optional[Dict[str, Any]] = None
    provenance_status: str = "VALID"
    is_malformed: bool = False


@dataclass
class StructuredDataset:
    dataset_id: str
    title: str
    description: str = ""
    columns: List[str] = field(default_factory=list)
    records: List[StructuredRecord] = field(default_factory=list)
    source_id: str = ""
    canonical_url: str = ""
    data_type: StructuredDataType = StructuredDataType.DATASET
    truncated: bool = False
    truncation_reason: Optional[str] = None
    total_records_detected: int = 0
    records_returned: int = 0


@dataclass
class ResourceCandidate:
    url: str
    canonical_url: str
    resource_type: str  # e.g. PDF, CSV, JSON, XML, RSS, ATOM, ZIP
    mime_type: str
    anchor_text: str
    source_id: str
    is_url_safe: bool = True
    is_eligible: bool = True
    rejection_reason: LinkRejectionReason = LinkRejectionReason.NONE
    handoff_target: Optional[str] = None  # e.g. "I2.3_DOCUMENT_INTELLIGENCE"
    fetched: bool = False


@dataclass
class PaginationMetadata:
    has_pagination: bool = False
    current_page: int = 1
    next_page_url: Optional[str] = None
    previous_page_url: Optional[str] = None
    estimated_total_pages: Optional[int] = None
    pagination_type: str = "QUERY_PARAM"  # rel_next, query_param, cursor


@dataclass
class StructuredExtractionResult:
    detected_types: List[StructuredDataType] = field(default_factory=list)
    records: List[StructuredRecord] = field(default_factory=list)
    datasets: List[StructuredDataset] = field(default_factory=list)
    resources: List[ResourceCandidate] = field(default_factory=list)
    pagination: Optional[PaginationMetadata] = None
    warnings: List[str] = field(default_factory=list)
    source_id: str = ""
    canonical_url: str = ""


@dataclass
class StructuredWebRequest:
    query: str
    urls: List[str] = field(default_factory=list)
    max_records: int = 20
    allow_resource_discovery: bool = True
    allow_pagination: bool = True
    conversation_id: Optional[str] = None


@dataclass
class StructuredWebResponse:
    status: str
    query: str
    detected_types: List[StructuredDataType] = field(default_factory=list)
    selected_records: List[StructuredRecord] = field(default_factory=list)
    datasets: List[StructuredDataset] = field(default_factory=list)
    resources: List[ResourceCandidate] = field(default_factory=list)
    pagination: Optional[PaginationMetadata] = None
    serialized_context: str = ""
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


# Hard Server Configurations
class StructuredConfig:
    MAX_STRUCTURED_PAGES: int = 5
    MAX_TABLES_PER_PAGE: int = 10
    MAX_TABLE_ROWS: int = 200
    MAX_TABLE_COLUMNS: int = 30
    MAX_JSON_DEPTH: int = 12
    MAX_JSON_RECORDS: int = 500
    MAX_JSON_STRING_LENGTH: int = 10_000
    MAX_JSON_NODES: int = 5000
    MAX_CSV_BYTES: int = 500_000  # 500 KB
    MAX_CSV_ROWS: int = 500
    MAX_CSV_COLUMNS: int = 50
    MAX_CSV_CELL_LENGTH: int = 1000
    MAX_FEED_ENTRIES: int = 100
    MAX_RESOURCES: int = 50
    MAX_PAGINATION_PAGES: int = 3
    MAX_SELECTED_RECORDS: int = 50
    MAX_STRUCTURED_CONTEXT_CHARS: int = 15_000
    MAX_WALL_CLOCK_SECONDS: float = 20.0
