import time
from typing import Dict, Optional, Any, Tuple
from common.cache.interfaces import BaseCacheProvider
from tools.telemetry import log_structured, backend_log


class MemoryCacheProvider:
    """
    In-memory cache provider implementation for Patch 7.0.1.
    Supports TTL expiration, hit/miss telemetry, and clean key eviction.
    """

    def __init__(self, default_ttl_sec: float = 3600.0):
        self.default_ttl_sec = default_ttl_sec
        # Internal store: {key: (value, expire_timestamp)}
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    def _is_expired(self, expire_at: Optional[float]) -> bool:
        if expire_at is None:
            return False
        return time.time() > expire_at

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            self._misses += 1
            return None

        val, expire_at = item
        if self._is_expired(expire_at):
            del self._store[key]
            self._evictions += 1
            self._misses += 1
            return None

        self._hits += 1
        return val

    def set(self, key: str, value: Any, ttl_sec: Optional[float] = None) -> bool:
        ttl_val = ttl_sec if ttl_sec is not None else self.default_ttl_sec
        expire_at = (time.time() + ttl_val) if ttl_val > 0 else None
        self._store[key] = (value, expire_at)
        return True

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> bool:
        self._store.clear()
        return True

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def ttl(self, key: str) -> Optional[float]:
        item = self._store.get(key)
        if not item:
            return None
        _, expire_at = item
        if expire_at is None:
            return -1.0  # Persistent key
        remaining = expire_at - time.time()
        return max(0.0, remaining)

    def statistics(self) -> Dict[str, Any]:
        total_requests = self._hits + self._misses
        hit_ratio = (self._hits / float(total_requests)) if total_requests > 0 else 1.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "total_keys": len(self._store),
            "hit_ratio": round(hit_ratio, 4),
        }
