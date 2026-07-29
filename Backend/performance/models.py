"""
Data models and statistics structures for J.A.R.V.I.S. Phase V1.7 Performance Engine.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class LatencyMetrics:
    """Quantitative latency statistics breakdown."""
    operation: str = "default"
    sample_count: int = 0
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p90_ms: float = 0.0
    p99_ms: float = 0.0


@dataclass
class MemoryStatistics:
    """Process memory allocation and garbage collection metrics."""
    rss_mb: float = 0.0
    vms_mb: float = 0.0
    peak_mb: float = 0.0
    gc_gen0_collections: int = 0
    gc_gen1_collections: int = 0
    gc_gen2_collections: int = 0
    allocation_count: int = 0


@dataclass
class CPUStatistics:
    """CPU utilization breakdown."""
    cpu_percent: float = 0.0
    thread_count: int = 1
    user_time_sec: float = 0.0
    system_time_sec: float = 0.0


@dataclass
class QueueStatistics:
    """Event & Task queue telemetry."""
    queue_name: str = "default"
    current_size: int = 0
    max_capacity: int = 1000
    total_enqueued: int = 0
    total_dequeued: int = 0
    overflow_drops: int = 0


@dataclass
class ResourceStatistics:
    """Resource pool allocation telemetry."""
    pool_name: str = "default"
    total_resources: int = 0
    in_use: int = 0
    available: int = 0
    reuse_count: int = 0


@dataclass
class TaskStatistics:
    """Task scheduler execution telemetry."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    active_workers: int = 0


@dataclass
class BenchmarkResult:
    """Output summary of a synthetic workload benchmark test run."""
    benchmark_name: str = ""
    iterations: int = 0
    total_time_sec: float = 0.0
    throughput_ops_sec: float = 0.0
    latency_avg_ms: float = 0.0
    latency_p99_ms: float = 0.0
    passed: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryStatistics:
    """Retry manager execution statistics."""
    total_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    exhausted_retries: int = 0


@dataclass
class CircuitBreakerStatistics:
    """Circuit breaker state telemetry."""
    state: str = "CLOSED"
    failure_count: int = 0
    success_count: int = 0
    trip_count: int = 0
    last_state_change: float = field(default_factory=time.time)


@dataclass
class PerformanceSnapshot:
    """Point-in-time system performance snapshot."""
    timestamp: float = field(default_factory=time.time)
    latency_p50: float = 0.0
    latency_p90: float = 0.0
    latency_p99: float = 0.0
    rss_memory_mb: float = 0.0
    cpu_percent: float = 0.0
    active_workers: int = 0
    queue_depth: int = 0
    health_score: float = 100.0
