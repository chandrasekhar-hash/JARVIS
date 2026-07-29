"""
Master Performance Engine Entrypoint for J.A.R.V.I.S. Phase V1.7.
Exposes start(), stop(), profile(), benchmark(), optimize(), get_metrics(), get_statistics(), health(), set_profile().
"""
import logging
from typing import Optional, Dict, Any, List

from .config import PerformanceConfig, performance_config
from .profiles import PerformanceProfileManager
from .models import PerformanceSnapshot, BenchmarkResult
from .coordinator import PerformanceCoordinator
from .benchmark import BenchmarkRunner
from .metrics import PerformanceMetrics
from .reports import ReportGenerator

logger = logging.getLogger("JARVIS_PerformanceEngine")


class PerformanceEngine:
    """
    Master Performance & Reliability Engine Entrypoint.
    """

    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or performance_config
        self.coordinator = PerformanceCoordinator(config=self.config)
        self.benchmark_runner = BenchmarkRunner(profiler=self.coordinator.performance_manager.profiler)
        self.metrics = PerformanceMetrics(coordinator=self.coordinator)
        self._running: bool = False

    async def start(self) -> None:
        """Starts the Performance Engine."""
        self._running = True
        await self.coordinator.start()
        logger.info(f"[PerformanceEngine] Started successfully with profile '{self.config.profile_name}'.")

    async def stop(self) -> None:
        """Stops the Performance Engine cleanly."""
        self._running = False
        await self.coordinator.stop()
        logger.info("[PerformanceEngine] Stopped cleanly.")

    def set_profile(self, profile_name: str) -> None:
        """Switches active performance configuration profile preset."""
        new_config = PerformanceProfileManager.get_profile(profile_name)
        self.config = new_config
        self.coordinator.config = new_config
        self.coordinator.performance_manager.config = new_config
        self.coordinator.reliability_manager.config = new_config
        logger.info(f"[PerformanceEngine] Switched active profile preset to '{profile_name}'.")

    def profile(self, operation: str, latency_ms: float) -> None:
        """Records latency execution sample for an operation."""
        self.coordinator.performance_manager.record_operation_latency(operation, latency_ms)

    async def benchmark(self, name: str = "SyntheticWorkload", iterations: int = 50) -> BenchmarkResult:
        """Runs a synthetic benchmark workload test."""
        return await self.benchmark_runner.run_benchmark(name, iterations)

    def optimize(self) -> None:
        """Triggers dynamic self-tuning pass."""
        self.coordinator.performance_manager.tune()

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot telemetry summary."""
        return self.metrics.get_summary()

    def get_statistics(self) -> PerformanceSnapshot:
        """Returns point-in-time performance snapshot."""
        return self.coordinator.get_snapshot()

    def health(self) -> Dict[str, Any]:
        """Returns health score breakdown."""
        return self.coordinator.reliability_manager.health_scorer.get_health_breakdown()

    def generate_report(self, benchmark_results: Optional[List[BenchmarkResult]] = None) -> str:
        """Generates structured Markdown performance report."""
        snapshot = self.get_statistics()
        b_results = benchmark_results or []
        return ReportGenerator.generate_markdown_report(snapshot, b_results)


# Global singleton instance
performance_engine = PerformanceEngine()
