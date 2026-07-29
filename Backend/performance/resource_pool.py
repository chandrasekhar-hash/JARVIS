"""
Resource Object Pool for J.A.R.V.I.S. Phase V1.7.
Recycles byte buffers, audio frames, and objects to eliminate GC allocation overhead.
"""
import logging
from typing import List, Callable, Any, Optional
from .interfaces import IResourcePool
from .models import ResourceStatistics

logger = logging.getLogger("JARVIS_ResourcePool")


class ResourcePool(IResourcePool):
    """
    Reusable object pool for high-frequency allocations (PCM byte buffers, AudioFrames).
    """

    def __init__(self, factory_fn: Callable[[], Any], pool_name: str = "default", max_size: int = 100):
        self.factory_fn = factory_fn
        self.pool_name = pool_name
        self.max_size = max_size

        self._pool: List[Any] = [factory_fn() for _ in range(min(10, max_size))]
        self._in_use: int = 0
        self._total_created: int = len(self._pool)
        self._reuse_count: int = 0

    def acquire(self) -> Any:
        if self._pool:
            item = self._pool.pop()
            self._in_use += 1
            self._reuse_count += 1
            return item

        # Pool empty: instantiate new item if below limit
        item = self.factory_fn()
        self._total_created += 1
        self._in_use += 1
        return item

    def release(self, item: Any) -> None:
        if self._in_use > 0:
            self._in_use -= 1

        if len(self._pool) < self.max_size:
            self._pool.append(item)

    def get_statistics(self) -> ResourceStatistics:
        return ResourceStatistics(
            pool_name=self.pool_name,
            total_resources=self._total_created,
            in_use=self._in_use,
            available=len(self._pool),
            reuse_count=self._reuse_count,
        )
