"""
JARVIS Product 1.8 - Rate Limit Manager.
Sliding-window rate limiter enforcing per-provider API call quotas.
"""

import time
import logging
from typing import Dict, List
from .models import RateLimitConfig

logger = logging.getLogger(__name__)


class RateLimitManager:
    def __init__(self):
        self._timestamps: Dict[str, List[float]] = {}

    def check_rate_limit(self, provider: str, config: RateLimitConfig) -> bool:
        now = time.time()
        window_start = now - 60.0

        if provider not in self._timestamps:
            self._timestamps[provider] = []

        # Prune older timestamps
        self._timestamps[provider] = [t for t in self._timestamps[provider] if t >= window_start]

        if len(self._timestamps[provider]) >= config.requests_per_minute:
            logger.warning(f"Rate limit exceeded for provider '{provider}' ({len(self._timestamps[provider])}/{config.requests_per_minute} req/min).")
            return False

        self._timestamps[provider].append(now)
        return True
