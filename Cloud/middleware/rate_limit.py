import time
from typing import Dict, List
from fastapi import Request, HTTPException, status
from config.settings import cloud_settings

class RateLimiter:
    """
    Sliding window in-memory rate limiter per IP.
    Restricts endpoints to max requests per minute (default: 100).
    """

    def __init__(self, requests_per_minute: int = None):
        self.limit = requests_per_minute or cloud_settings.rate_limit_per_minute
        self.requests: Dict[str, List[float]] = {}

    def check_rate_limit(self, request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - 60.0

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Filter out timestamps older than 60 seconds
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]

        if len(self.requests[client_ip]) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.limit} requests per minute allowed."
            )

        self.requests[client_ip].append(now)

rate_limiter = RateLimiter()
