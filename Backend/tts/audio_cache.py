"""
In-Memory LRU Audio Cache for J.A.R.V.I.S. Phase V1.4 Voice Output Engine (TTS).
Caches synthesized TTSResult objects to avoid duplicate remote API calls and reduce latency.
"""
import hashlib
from collections import OrderedDict
from typing import Optional, Dict, Any
from .interfaces import IAudioCache
from .models import TTSResult
from .metrics import voice_metrics


class AudioCache(IAudioCache):
    """LRU Cache for synthesized audio results."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: OrderedDict[str, TTSResult] = OrderedDict()

    @staticmethod
    def generate_cache_key(text: str, voice_id: str, provider_name: str) -> str:
        """Generates deterministic MD5 hash key for text + voice + provider."""
        raw_key = f"{provider_name}:{voice_id}:{text.strip()}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[TTSResult]:
        if key in self._cache:
            res = self._cache[key]
            self._cache.move_to_end(key)  # Refresh LRU ordering
            voice_metrics.cache_hits += 1
            # Return fresh copy marked with cache_hit=True
            return TTSResult(
                session_id=res.session_id,
                provider=res.provider,
                voice_profile=res.voice_profile,
                latency_ms=0.5,
                audio_duration_ms=res.audio_duration_ms,
                cache_hit=True,
                chunk_count=res.chunk_count,
                audio_data=res.audio_data,
                success=True,
            )
        voice_metrics.cache_misses += 1
        return None

    def put(self, key: str, result: TTSResult) -> None:
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # Evict oldest item
        self._cache[key] = result

    def clear(self) -> None:
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_size": len(self._cache),
            "max_size": self.max_size,
            "hits": voice_metrics.cache_hits,
            "misses": voice_metrics.cache_misses,
        }
