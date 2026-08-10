"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Browser & Dynamic Web Models.
Defines data structures, enums, side-effect classifications, and server bounds for interactive web intelligence.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import time


class BrowserExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    STATIC_CONTENT_SUFFICIENT = "STATIC_CONTENT_SUFFICIENT"
    JS_RENDER_REQUIRED = "JS_RENDER_REQUIRED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PAYWALL = "PAYWALL"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    ACCESS_DENIED = "ACCESS_DENIED"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"
    SSRF_BLOCKED = "SSRF_BLOCKED"
    NO_RELEVANT_INTERACTION = "NO_RELEVANT_INTERACTION"
    ACTION_LIMIT_REACHED = "ACTION_LIMIT_REACHED"
    NAVIGATION_LIMIT_REACHED = "NAVIGATION_LIMIT_REACHED"
    TIMEOUT = "TIMEOUT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    PARTIAL = "PARTIAL"


class BrowserEscalationReason(str, Enum):
    JS_RENDER_REQUIRED = "JS_RENDER_REQUIRED"
    DYNAMIC_CONTENT_MISSING = "DYNAMIC_CONTENT_MISSING"
    INTERACTION_REQUIRED = "INTERACTION_REQUIRED"
    CLIENT_SIDE_PAGINATION = "CLIENT_SIDE_PAGINATION"
    DYNAMIC_TABLE = "DYNAMIC_TABLE"
    EXPANDABLE_CONTENT = "EXPANDABLE_CONTENT"
    EXPLICIT_USER_REQUEST = "EXPLICIT_USER_REQUEST"
    NONE = "NONE"


class BrowserActionType(str, Enum):
    OPEN_PAGE = "OPEN_PAGE"
    OBSERVE = "OBSERVE"
    SCROLL = "SCROLL"
    CLICK_SAFE = "CLICK_SAFE"
    EXPAND = "EXPAND"
    OPEN_TAB_CONTENT = "OPEN_TAB_CONTENT"
    NEXT_PAGE = "NEXT_PAGE"
    LOAD_MORE = "LOAD_MORE"
    SELECT_NON_SENSITIVE_FILTER = "SELECT_NON_SENSITIVE_FILTER"
    WAIT_FOR_DYNAMIC_CONTENT = "WAIT_FOR_DYNAMIC_CONTENT"


class SideEffectClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK_UI_STATE = "LOW_RISK_UI_STATE"
    FORM_MUTATION = "FORM_MUTATION"
    ACCOUNT_MUTATION = "ACCOUNT_MUTATION"
    COMMUNICATION = "COMMUNICATION"
    FINANCIAL = "FINANCIAL"
    DESTRUCTIVE = "DESTRUCTIVE"
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
class ElementRef:
    element_id: str  # e.g. "element_17"
    role: str
    accessible_name: str
    visible_text: str
    element_type: str
    selector_hint: str
    observation_id: str
    page_state_fingerprint: str
    is_interactive: bool = True
    is_safe: bool = True
    rejection_reason: Optional[str] = None


@dataclass
class BrowserPageObservation:
    observation_id: str
    canonical_url: str
    title: str
    visible_text: str
    headings: List[str] = field(default_factory=list)
    interactive_elements: List[ElementRef] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    lists: List[Dict[str, Any]] = field(default_factory=list)
    page_timestamp: float = field(default_factory=time.time)
    network_idle_status: bool = True
    content_fingerprint: str = ""


@dataclass
class BrowserActionPlan:
    action_id: str
    action_type: BrowserActionType
    target_element_id: Optional[str] = None
    reason: str = ""
    side_effect_class: SideEffectClass = SideEffectClass.READ_ONLY
    safety_status: str = "ALLOWED"


@dataclass
class BrowserEvidenceItem:
    evidence_id: str
    source_id: str
    canonical_url: str
    page_title: str
    content: str
    element_reference: Optional[str] = None
    interaction_chain: List[str] = field(default_factory=list)
    retrieved_at: str = ""
    source_path: str = ""
    provenance_status: str = "VALID"


@dataclass
class BrowserWebRequest:
    query: str
    url: Optional[str] = None
    conversation_id: Optional[str] = None
    allow_interaction: bool = True
    user_timezone: Optional[str] = None


@dataclass
class BrowserWebResponse:
    status: BrowserExecutionStatus
    escalation_reason: BrowserEscalationReason
    query: str
    canonical_url: str = ""
    title: str = ""
    evidence_items: List[BrowserEvidenceItem] = field(default_factory=list)
    interaction_chain: List[str] = field(default_factory=list)
    serialized_context: str = ""
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    security_audit: Dict[str, str] = field(default_factory=lambda: {
        "URL_VALIDATION": "VERIFIED",
        "DNS_RESOLUTION_VALIDATION": "VERIFIED",
        "REDIRECT_VALIDATION": "VERIFIED",
        "BROWSER_SOCKET_IP_PINNING": "PARTIAL",
    })


# Hard Server Configurations
class BrowserConfig:
    MAX_BROWSER_PAGES: int = 2
    MAX_BROWSER_ACTIONS: int = 12
    MAX_BROWSER_NAVIGATIONS: int = 6
    MAX_BROWSER_SCROLLS: int = 8
    MAX_BROWSER_SCREENSHOTS: int = 3
    MAX_ACTION_WAIT_SECONDS: float = 3.0
    MAX_BROWSER_CONTEXT_CHARS: int = 15_000
    MAX_BROWSER_RUNTIME_SECONDS: float = 25.0
    MAX_DYNAMIC_RECORDS: int = 100
    MAX_CONCURRENT_BROWSER_SESSIONS: int = 2

    # Memory & Observation Bounds
    MAX_VISIBLE_TEXT_CHARS: int = 30_000
    MAX_INTERACTIVE_ELEMENTS: int = 50
    MAX_LINKS: int = 50
    MAX_HEADINGS: int = 30
    MAX_TABLES: int = 10
    MAX_LISTS: int = 10
