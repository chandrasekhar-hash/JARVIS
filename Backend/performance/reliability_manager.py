"""
Reliability Manager for J.A.R.V.I.S. Phase V1.7.
Coordinating RetryManager, CircuitBreaker registry, WatchdogTimer, HealthScorer, MemoryMonitor.
"""
from typing import Optional, Dict, Any

from .config import PerformanceConfig, performance_config
from .retry import RetryManager
from .circuit_breaker import CircuitBreaker
from .watchdog import WatchdogTimer
from .health_score import HealthScorer
from .memory_monitor import MemoryMonitor


class ReliabilityManager:
    """
    Subsystem manager dedicated to fault tolerance, retries, circuit breaking, memory safety, and watchdog monitoring.
    """

    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or performance_config

        self.retry_manager = RetryManager(
            max_retries=self.config.max_retries,
            initial_delay_sec=self.config.retry_initial_delay_sec,
            backoff_factor=self.config.retry_backoff_factor,
        )

        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_scorer = HealthScorer()
        self.memory_monitor = MemoryMonitor()
        self.watchdog = WatchdogTimer(
            interval_sec=self.config.watchdog_interval_sec,
            scan_callback=self._watchdog_scan,
        )

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                recovery_timeout_sec=self.config.circuit_breaker_recovery_timeout_sec,
            )
        return self.circuit_breakers[name]

    def _watchdog_scan(self) -> None:
        """Watchdog scan routine checking memory usage and health thresholds."""
        mem_stats = self.memory_monitor.get_statistics()
        if mem_stats.rss_mb > self.config.max_memory_mb:
            self.memory_monitor.force_garbage_collection()

    async def start(self) -> None:
        await self.watchdog.start()

    async def stop(self) -> None:
        await self.watchdog.stop()

    def get_summary(self) -> Dict[str, Any]:
        return {
            "retry_stats": self.retry_manager.get_statistics().__dict__,
            "circuit_breakers": {name: cb.get_statistics().__dict__ for name, cb in self.circuit_breakers.items()},
            "memory": self.memory_monitor.get_statistics().__dict__,
            "health": self.health_scorer.get_health_breakdown(),
            "watchdog": self.watchdog.get_summary(),
        }
