"""
Performance Profiles for J.A.R.V.I.S. Phase V1.7.
Provides configuration presets: Development, Balanced, Low Latency, Battery Saver, Stress Testing.
"""
from typing import Dict
from .config import PerformanceConfig


class PerformanceProfileManager:
    """Manages performance configuration profiles."""

    PROFILES: Dict[str, PerformanceConfig] = {
        "Development": PerformanceConfig(
            profile_name="Development",
            initial_worker_count=2,
            max_worker_count=4,
            max_queue_size=200,
            watchdog_interval_sec=10.0,
            adaptive_tuning_enabled=False,
        ),
        "Balanced": PerformanceConfig(
            profile_name="Balanced",
            initial_worker_count=4,
            max_worker_count=16,
            max_queue_size=1000,
            watchdog_interval_sec=5.0,
            adaptive_tuning_enabled=True,
        ),
        "Low Latency": PerformanceConfig(
            profile_name="Low Latency",
            initial_worker_count=8,
            max_worker_count=32,
            max_queue_size=2000,
            cache_capacity=1000,
            watchdog_interval_sec=2.0,
            adaptive_tuning_enabled=True,
            wake_word_budget_ms=15.0,
            audio_budget_ms=5.0,
            speech_recognition_budget_ms=200.0,
            conversation_budget_ms=500.0,
            tts_start_budget_ms=200.0,
        ),
        "Battery Saver": PerformanceConfig(
            profile_name="Battery Saver",
            initial_worker_count=1,
            max_worker_count=4,
            max_queue_size=500,
            watchdog_interval_sec=15.0,
            adaptive_tuning_enabled=False,
        ),
        "Stress Testing": PerformanceConfig(
            profile_name="Stress Testing",
            initial_worker_count=16,
            max_worker_count=64,
            max_queue_size=5000,
            cache_capacity=2000,
            watchdog_interval_sec=1.0,
            benchmark_iterations=200,
            adaptive_tuning_enabled=True,
        ),
    }

    @classmethod
    def get_profile(cls, name: str) -> PerformanceConfig:
        return cls.PROFILES.get(name, cls.PROFILES["Balanced"])
