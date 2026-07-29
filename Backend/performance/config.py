"""
Configuration Layer for J.A.R.V.I.S. Phase V1.7 Performance & Reliability Engine.
Centralized settings for memory limits, queue sizes, resource pools, retry backoff,
circuit breaker thresholds, cache capacity/TTL, benchmark runs, and performance budgets.
"""
from dataclasses import dataclass, field


@dataclass
class PerformanceConfig:
    """Centralized Performance & Reliability Configuration."""
    profile_name: str = "Balanced"
    max_memory_mb: float = 1024.0
    max_queue_size: int = 1000
    max_pool_size: int = 100
    initial_worker_count: int = 4
    max_worker_count: int = 16
    task_timeout_sec: float = 30.0
    watchdog_interval_sec: float = 5.0
    
    # Retry & Circuit Breaker settings
    max_retries: int = 3
    retry_backoff_factor: float = 1.5
    retry_initial_delay_sec: float = 0.1
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_sec: float = 10.0

    # Cache settings
    cache_capacity: int = 500
    cache_ttl_sec: float = 300.0

    # Adaptive tuning toggles
    adaptive_tuning_enabled: bool = True
    adaptive_check_interval_sec: float = 2.0
    high_latency_threshold_ms: float = 300.0
    low_latency_threshold_ms: float = 50.0

    # Benchmark settings
    benchmark_iterations: int = 50
    sampling_interval_sec: float = 1.0

    # SLA Performance Budgets (ms)
    wake_word_budget_ms: float = 20.0
    audio_budget_ms: float = 10.0
    speech_recognition_budget_ms: float = 250.0
    conversation_budget_ms: float = 700.0
    tts_start_budget_ms: float = 300.0
    event_routing_budget_ms: float = 5.0


# Global default configuration instance
performance_config = PerformanceConfig()
