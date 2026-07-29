"""
Data Models and Diagnostic Structures for J.A.R.V.I.S. Phase V1.8.
Includes LogEntry, TraceRecord, SpanRecord, TimelineRecord, SubsystemStatus,
StartupCheck, RuntimeCheck, HealthSnapshot, SessionSnapshot, DashboardSnapshot, DiagnosticResult.
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class LogEntry:
    """Structured Log Entry."""
    timestamp: float = field(default_factory=time.time)
    level: str = "INFO"
    subsystem: str = "SYSTEM"
    message: str = ""
    correlation_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanRecord:
    """Individual span in a distributed trace."""
    span_id: str = field(default_factory=lambda: f"spn_{uuid.uuid4().hex[:12]}")
    trace_id: str = ""
    parent_span_id: Optional[str] = None
    operation: str = ""
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceRecord:
    """Distributed trace tree container."""
    trace_id: str = field(default_factory=lambda: f"trc_{uuid.uuid4().hex[:12]}")
    correlation_id: str = ""
    root_operation: str = ""
    spans: List[SpanRecord] = field(default_factory=list)
    total_duration_ms: float = 0.0


@dataclass
class TimelineRecord:
    """Chronological event timeline record."""
    record_id: str = field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:12]}")
    event_name: str = ""
    subsystem: str = ""
    session_id: str = ""
    correlation_id: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventRecord:
    """Event representation for timeline replay."""
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubsystemStatus:
    """Subsystem health status snapshot."""
    subsystem_name: str
    healthy: bool = True
    latency_ms: float = 0.0
    last_activity_sec_ago: float = 0.0
    error_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StartupCheck:
    """Startup environment and configuration verification check."""
    check_name: str
    passed: bool = True
    details: str = "Passed"


@dataclass
class RuntimeCheck:
    """Runtime deadlock and queue congestion check."""
    check_name: str
    passed: bool = True
    warning_level: str = "NONE"  # NONE, WARNING, CRITICAL
    details: str = "Nominal"


@dataclass
class HealthSnapshot:
    """Aggregated health snapshot."""
    timestamp: float = field(default_factory=time.time)
    overall_healthy: bool = True
    overall_score: float = 100.0
    subsystems: Dict[str, SubsystemStatus] = field(default_factory=dict)


@dataclass
class SessionSnapshot:
    """Session state snapshot."""
    session_id: str
    state: str = "IDLE"
    turn_count: int = 0
    duration_sec: float = 0.0
    barge_ins: int = 0
    errors: int = 0


@dataclass
class DashboardSnapshot:
    """Real-time diagnostic dashboard snapshot."""
    timestamp: float = field(default_factory=time.time)
    health_score: float = 100.0
    latency_p50: float = 0.0
    latency_p99: float = 0.0
    rss_memory_mb: float = 0.0
    queue_depth: int = 0
    active_workers: int = 0
    active_sessions: int = 0
    total_events: int = 0


@dataclass
class DiagnosticResult:
    """Summary result returned by diagnostic operations."""
    success: bool = True
    timestamp: float = field(default_factory=time.time)
    diagnostics_summary: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
