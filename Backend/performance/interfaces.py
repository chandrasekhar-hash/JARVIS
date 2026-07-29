"""
Abstract Interfaces for J.A.R.V.I.S. Phase V1.7 Performance Engine.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
from .models import (
    LatencyMetrics,
    MemoryStatistics,
    QueueStatistics,
    ResourceStatistics,
    TaskStatistics,
    BenchmarkResult,
    PerformanceSnapshot,
)


class IPerformanceProfiler(ABC):
    """Abstract interface for Performance Profiler."""

    @abstractmethod
    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Records an execution latency sample for an operation."""
        pass

    @abstractmethod
    def get_metrics(self, operation: str = "default") -> LatencyMetrics:
        """Returns latency statistics breakdown for target operation."""
        pass


class ITaskScheduler(ABC):
    """Abstract interface for Priority Task Scheduler."""

    @abstractmethod
    async def schedule(self, coro_fn: Callable, priority: int = 5, task_name: str = "") -> Any:
        """Schedules an asynchronous task with given priority."""
        pass

    @abstractmethod
    def cancel(self, task_name: str) -> bool:
        """Cancels a scheduled task by name."""
        pass


class IResourcePool(ABC):
    """Abstract interface for Resource Object Pool."""

    @abstractmethod
    def acquire(self) -> Any:
        """Acquires a resource object from pool."""
        pass

    @abstractmethod
    def release(self, item: Any) -> None:
        """Releases a resource object back to pool."""
        pass


class IQueueManager(ABC):
    """Abstract interface for Priority Event Queue Manager."""

    @abstractmethod
    async def enqueue(self, queue_name: str, item: Any, priority: int = 5) -> bool:
        """Enqueues an item with priority."""
        pass

    @abstractmethod
    async def dequeue(self, queue_name: str) -> Any:
        """Dequeues highest priority item from queue."""
        pass


class IRetryManager(ABC):
    """Abstract interface for Retry Manager."""

    @abstractmethod
    async def execute_with_retry(self, fn: Callable, *args, **kwargs) -> Any:
        """Executes function with exponential backoff retries."""
        pass


class ICircuitBreaker(ABC):
    """Abstract interface for Circuit Breaker."""

    @abstractmethod
    def can_execute(self) -> bool:
        """Returns True if circuit breaker allows execution."""
        pass

    @abstractmethod
    def record_success(self) -> None:
        """Records a successful operation."""
        pass

    @abstractmethod
    def record_failure(self, error: Exception) -> None:
        """Records a failed operation."""
        pass


class ICache(ABC):
    """Abstract interface for LRU Cache."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieves item by key from cache."""
        pass

    @abstractmethod
    def put(self, key: str, value: Any, ttl_sec: Optional[float] = None) -> None:
        """Stores item in cache with optional TTL."""
        pass


class IMemoryMonitor(ABC):
    """Abstract interface for Memory Monitor."""

    @abstractmethod
    def get_statistics(self) -> MemoryStatistics:
        """Returns current process memory statistics."""
        pass


class IBenchmarkRunner(ABC):
    """Abstract interface for Synthetic Benchmark Runner."""

    @abstractmethod
    async def run_benchmark(self, name: str, iterations: int = 50) -> BenchmarkResult:
        """Executes target benchmark suite."""
        pass
