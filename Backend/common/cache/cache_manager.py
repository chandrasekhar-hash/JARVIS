from typing import Optional, Dict, Any
from common.cache.interfaces import BaseCacheProvider
from common.cache.memory_cache import MemoryCacheProvider
from tools.telemetry import log_structured, backend_log


class CacheManager:
    """
    Central Cache Manager delegating operations to active BaseCacheProvider implementation.
    Prepared for future distributed Redis provider integration.
    """

    def __init__(self, provider: Optional[BaseCacheProvider] = None):
        self._provider = provider or MemoryCacheProvider()

    def set_provider(self, provider: BaseCacheProvider) -> None:
        """Dynamically swaps the cache provider."""
        self._provider = provider
        log_structured(backend_log, "INFO", "[CacheManager] Swapped cache provider")

    def get(self, key: str) -> Optional[Any]:
        return self._provider.get(key)

    def set(self, key: str, value: Any, ttl_sec: Optional[float] = None) -> bool:
        return self._provider.set(key, value, ttl_sec=ttl_sec)

    def delete(self, key: str) -> bool:
        return self._provider.delete(key)

    def clear(self) -> bool:
        return self._provider.clear()

    def exists(self, key: str) -> bool:
        return self._provider.exists(key)

    def ttl(self, key: str) -> Optional[float]:
        return self._provider.ttl(key)

    def statistics(self) -> Dict[str, Any]:
        return self._provider.statistics()


# Default global cache manager instance
cache_manager = CacheManager()
