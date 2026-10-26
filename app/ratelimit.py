"""Simple in-memory per-IP rate limiter."""

import time
from collections import defaultdict
from fastapi import HTTPException, Request


class RateLimiter:
    """Token bucket rate limiter keyed by IP address."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, request: Request) -> None:
        """Raise 429 if rate limit exceeded."""
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window_seconds

        # Prune old entries
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]

        if len(self._requests[ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds // 60} minutes."
            )

        self._requests[ip].append(now)


# Global instance: 30 review runs per hour per IP
review_limiter = RateLimiter(max_requests=30, window_seconds=3600)
