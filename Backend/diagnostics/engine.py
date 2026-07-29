"""
Master Diagnostics Engine Entrypoint for J.A.R.V.I.S. Phase V1.8.
Exposes start(), stop(), log(), trace(), timeline(), dashboard(), health(),
startup_check(), runtime_check(), generate_report(), export(), export_trace(), export_timeline().
"""
import logging
from typing import Optional, Dict, Any, List

from .config import DiagnosticsConfig, diagnostics_config
from .coordinator import DiagnosticsCoordinator
from .models import (
    DiagnosticResult,
    HealthSnapshot,
    DashboardSnapshot,
    TraceRecord,
    TimelineRecord,
    StartupCheck,
    RuntimeCheck,
)

logger = logging.getLogger("JARVIS_DiagnosticsEngine")


class DiagnosticsEngine:
    """
    Master Developer Diagnostics & Observability Engine.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or diagnostics_config
        self.coordinator = DiagnosticsCoordinator(config=self.config)
        self._running: bool = False

    async def start(self) -> None:
        """Starts the Diagnostics Engine."""
        self._running = True
        await self.coordinator.start()
        logger.info("[DiagnosticsEngine] Started successfully.")

    async def stop(self) -> None:
        """Stops the Diagnostics Engine cleanly."""
        self._running = False
        await self.coordinator.stop()
        logger.info("[DiagnosticsEngine] Stopped cleanly.")

    def log(self, level: str, subsystem: str, message: str, correlation_id: str = "", **kwargs) -> None:
        """Logs structured message."""
        self.coordinator.logger.log(level, subsystem, message, correlation_id, **kwargs)

    def trace(self, root_operation: str, correlation_id: str = "") -> TraceRecord:
        """Starts a distributed trace."""
        return self.coordinator.tracer.start_trace(root_operation, correlation_id)

    def timeline(self, session_id: Optional[str] = None) -> List[TimelineRecord]:
        """Returns recorded event timeline."""
        return self.coordinator.timeline_recorder.get_timeline(session_id=session_id)

    def dashboard(self) -> DashboardSnapshot:
        """Returns real-time dashboard snapshot."""
        return self.coordinator.dashboard_generator.get_snapshot()

    def health(self) -> HealthSnapshot:
        """Returns health snapshot evaluation."""
        return self.coordinator.get_health()

    def startup_check(self) -> List[StartupCheck]:
        """Executes startup validation checks."""
        return self.coordinator.run_startup_checks()

    def runtime_check(self) -> List[RuntimeCheck]:
        """Executes runtime diagnostic stability checks."""
        return self.coordinator.run_runtime_checks()

    def generate_report(self) -> str:
        """Generates structured Markdown diagnostic report."""
        return self.coordinator.generate_report()

    def export(self, data: Any, format_type: str = "json", destination: str = "") -> str:
        """Exports diagnostic data in specified format."""
        return self.coordinator.exporter.export(data, format_type, destination)

    def export_trace(self, trace_id: str, destination: str = "") -> str:
        """Exports specific trace record as JSON."""
        trace = self.coordinator.tracer.get_trace(trace_id)
        if trace:
            return self.coordinator.exporter.export(trace, "json", destination)
        return ""

    def export_timeline(self, session_id: Optional[str] = None, destination: str = "") -> str:
        """Exports timeline event replay records as JSON."""
        replay = self.coordinator.timeline_recorder.replay_timeline(session_id=session_id)
        return self.coordinator.exporter.export([r.__dict__ for r in replay], "json", destination)


# Global singleton instance
diagnostics_engine = DiagnosticsEngine()
