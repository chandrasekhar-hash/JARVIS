"""
Metrics Registry for J.A.R.V.I.S. Phase V1.7.
Provides standard observability primitives: Counter, Gauge, Histogram, Timer.
"""
import time
import math
from typing import Dict, List, Optional, Any


class Counter:
    """Monotonically increasing counter metric."""
    def __init__(self, name: str):
        self.name = name
        self.value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        if amount > 0:
            self.value += amount

    def get(self) -> float:
        return self.value


class Gauge:
    """Instantaneous numerical gauge metric."""
    def __init__(self, name: str):
        self.name = name
        self.value: float = 0.0

    def set(self, val: float) -> None:
        self.value = val

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount

    def dec(self, amount: float = 1.0) -> None:
        self.value -= amount

    def get(self) -> float:
        return self.value


class Histogram:
    """Distribution histogram sampler for percentile analysis."""
    def __init__(self, name: str, history_capacity: int = 1000):
        self.name = name
        self.capacity = history_capacity
        self.samples: List[float] = []

    def observe(self, val: float) -> None:
        self.samples.append(val)
        if len(self.samples) > self.capacity:
            self.samples.pop(0)

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(math.ceil((p / 100.0) * len(sorted_samples))) - 1
        idx = max(0, min(idx, len(sorted_samples) - 1))
        return sorted_samples[idx]

    def avg(self) -> float:
        return sum(self.samples) / len(self.samples) if self.samples else 0.0


class Timer:
    """Latency timer metric."""
    def __init__(self, name: str, histogram: Histogram):
        self.name = name
        self.histogram = histogram

    def record(self, duration_ms: float) -> None:
        self.histogram.observe(duration_ms)


class MetricsRegistry:
    """Central observability registry holding Counters, Gauges, Histograms, and Timers."""
    def __init__(self):
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.timers: Dict[str, Timer] = {}

    def counter(self, name: str) -> Counter:
        if name not in self.counters:
            self.counters[name] = Counter(name)
        return self.counters[name]

    def gauge(self, name: str) -> Gauge:
        if name not in self.gauges:
            self.gauges[name] = Gauge(name)
        return self.gauges[name]

    def histogram(self, name: str) -> Histogram:
        if name not in self.histograms:
            self.histograms[name] = Histogram(name)
        return self.histograms[name]

    def timer(self, name: str) -> Timer:
        if name not in self.timers:
            hist = self.histogram(f"{name}_ms")
            self.timers[name] = Timer(name, hist)
        return self.timers[name]

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "counters": {k: v.get() for k, v in self.counters.items()},
            "gauges": {k: v.get() for k, v in self.gauges.items()},
            "histograms": {
                k: {
                    "count": len(v.samples),
                    "avg": round(v.avg(), 2),
                    "p50": round(v.percentile(50), 2),
                    "p90": round(v.percentile(90), 2),
                    "p99": round(v.percentile(99), 2),
                }
                for k, v in self.histograms.items()
            },
        }


# Global singleton instance
metrics_registry = MetricsRegistry()
