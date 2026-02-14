"""Token bucket rate limiter for the REST API."""

import time
from collections import defaultdict
from threading import Lock


class TokenBucket:
    """Simple token bucket rate limiter — per-key rate limiting."""

    def __init__(self, rate: int = 100, period: int = 60):
        """
        Args:
            rate: Number of allowed requests per period.
            period: Time period in seconds (default: 60 = 1 minute).
        """
        self.rate = rate
        self.period = period
        self._buckets: dict[str, dict] = defaultdict(lambda: {
            "tokens": rate,
            "last_refill": time.monotonic(),
        })
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Check if a request is allowed for the given key."""
        with self._lock:
            bucket = self._buckets[key]
            now = time.monotonic()
            elapsed = now - bucket["last_refill"]

            # Refill tokens
            refill = elapsed * (self.rate / self.period)
            bucket["tokens"] = min(self.rate, bucket["tokens"] + refill)
            bucket["last_refill"] = now

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True
            return False

    def remaining(self, key: str) -> int:
        """Return remaining tokens for a key."""
        with self._lock:
            bucket = self._buckets[key]
            now = time.monotonic()
            elapsed = now - bucket["last_refill"]
            refill = elapsed * (self.rate / self.period)
            return int(min(self.rate, bucket["tokens"] + refill))


# Global rate limiter instance
api_rate_limiter = TokenBucket(rate=100, period=60)
