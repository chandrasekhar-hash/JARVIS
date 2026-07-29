"""
High-Performance LRU Cache for J.A.R.V.I.S. Phase V1.7.
Supports TTL expiration, LRU eviction, and hit/miss statistics.
"""
import time
from collections import OrderedDict
from typing import Optional, Any, Dict
from .interfaces import ICache


class LRUCache(ICache):
    """
    LRU Cache implementation with TTL support.
    """

    def __init__(self, capacity: int = 500, default_ttl_sec: float = 300.0):
        self.capacity = capacity
        self.default_ttl_sec = default_ttl_sec
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        self.hits: int = 0
        self.misses: int = 0
        self.evictions: int = 0

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            self.misses += 1
            return None

        entry = self._cache[key]
        expire_at = entry["expire_at"]

        # Check TTL expiration
        if expire_at is not None and time.time() > expire_at:
            del self._cache[key]
            self.misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self.hits += 1
        return entry["value"]

    def put(self, key: str, value: Any, ttl_sec: Optional[float] = None) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)

        ttl = ttl_sec if ttl_sec is not None else self.default_ttl_sec
        expire_at = time.time() + ttl if ttl > 0 else None

        self._cache[key] = {"value": value, "expire_at": expire_at}

        # Check capacity eviction
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)  # pop least recently used
            self.evictions += 1

    def clear(self) -> None:
        self._cache.clear()

    def get_statistics(self) -> Dict[str, Any]:
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100.0) if total_requests > 0 else 0.0
        return {
            "capacity": self.capacity,
            "current_size": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate_percent": round(hit_rate, 2),
        }
