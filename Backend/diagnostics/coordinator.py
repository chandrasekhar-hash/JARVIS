"""
Diagnostics Coordinator for J.A.R.V.I.S. Phase V1.8.
Directs execution across Logger, Tracer, TimelineRecorder, HealthChecker, StartupValidator, RuntimeMonitor, DashboardGenerator, Exporters, and MetricsBridge.
"""
from typing import Optional, Dict, Any, List

from .config import DiagnosticsConfig, diagnostics_config
from .logger import StructuredLogger
from .tracer import DistributedTracer
from .timeline import TimelineRecorder
from .health import HealthChecker
from .startup import StartupValidator
from .runtime import RuntimeDiagnosticMonitor
from .dashboard import DashboardGenerator
from .metrics_bridge import MetricsBridge
from .exporters import DiagnosticsExporter
from .report import DiagnosticReportGenerator
from .models import (
    DiagnosticResult,
    HealthSnapshot,
    DashboardSnapshot,
    StartupCheck,
    RuntimeCheck,
)


class DiagnosticsCoordinator:
    """
    Global Coordinator directing execution across Developer Diagnostics & Observability components.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or diagnostics_config

        self.logger = StructuredLogger(config=self.config)
        self.tracer = DistributedTracer()
        self.timeline_recorder = TimelineRecorder(capacity=self.config.max_timeline_records)
        self.health_checker = HealthChecker()
        self.startup_validator = StartupValidator()
        self.runtime_monitor = RuntimeDiagnosticMonitor()
        self.dashboard_generator = DashboardGenerator(health_checker=self.health_checker)
        self.metrics_bridge = MetricsBridge()
        self.exporter = DiagnosticsExporter(config=self.config)

    async def start(self) -> None:
        self.logger.info("Diagnostics", "Developer Diagnostics & Observability Platform started.")

    async def stop(self) -> None:
        self.logger.info("Diagnostics", "Developer Diagnostics & Observability Platform stopped.")

    def run_startup_checks(self) -> List[StartupCheck]:
        return self.startup_validator.run_all_checks()

    def run_runtime_checks(self) -> List[RuntimeCheck]:
        return self.runtime_monitor.run_runtime_checks()

    def get_health(self) -> HealthSnapshot:
        return self.health_checker.check_health()

    def get_dashboard(self) -> DashboardSnapshot:
        return self.dashboard_generator.get_snapshot()

    def generate_report(self) -> str:
        health_snap = self.get_health()
        dash_snap = self.get_dashboard()
        startup_checks = self.run_startup_checks()
        runtime_checks = self.run_runtime_checks()
        return DiagnosticReportGenerator.generate_report(health_snap, dash_snap, startup_checks, runtime_checks)
