"""
Abstract Base Classes & Interfaces for J.A.R.V.I.S. Phase V1.8 Diagnostics Platform.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .models import (
    LogEntry,
    TraceRecord,
    SpanRecord,
    TimelineRecord,
    HealthSnapshot,
    DashboardSnapshot,
    StartupCheck,
    RuntimeCheck,
    DiagnosticResult,
)


class ILogger(ABC):
    """Abstract interface for Structured Logger."""

    @abstractmethod
    def log(self, level: str, subsystem: str, message: str, correlation_id: str = "", **kwargs) -> None:
        """Logs structured message."""
        pass


class ITracer(ABC):
    """Abstract interface for Distributed Tracer."""

    @abstractmethod
    def start_trace(self, root_operation: str, correlation_id: str = "") -> TraceRecord:
        """Starts a new distributed trace."""
        pass

    @abstractmethod
    def start_span(self, trace_id: str, operation: str, parent_span_id: Optional[str] = None) -> SpanRecord:
        """Starts a child span within trace."""
        pass

    @abstractmethod
    def finish_span(self, span_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Finishes active span."""
        pass


class ITimelineRecorder(ABC):
    """Abstract interface for Timeline Event Recorder."""

    @abstractmethod
    def record_event(self, event_name: str, subsystem: str, session_id: str = "", correlation_id: str = "", **payload) -> TimelineRecord:
        """Records chronological event."""
        pass

    @abstractmethod
    def get_timeline(self, session_id: Optional[str] = None) -> List[TimelineRecord]:
        """Returns recorded event timeline."""
        pass


class IHealthChecker(ABC):
    """Abstract interface for Health Checker."""

    @abstractmethod
    def check_health(self) -> HealthSnapshot:
        """Performs full health check evaluation."""
        pass


class IDashboard(ABC):
    """Abstract interface for Dashboard Generator."""

    @abstractmethod
    def get_snapshot(self) -> DashboardSnapshot:
        """Returns real-time dashboard snapshot."""
        pass


class IExporter(ABC):
    """Abstract interface for Diagnostics Exporter."""

    @abstractmethod
    def export(self, data: Any, format_type: str = "json", destination: str = "") -> str:
        """Exports diagnostic data in target format."""
        pass


class IDiagnosticsEngine(ABC):
    """Abstract interface for Master Diagnostics Engine."""

    @abstractmethod
    async def start(self) -> None:
        """Starts diagnostics platform."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops diagnostics platform."""
        pass
