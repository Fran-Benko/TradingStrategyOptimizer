"""
Rate limiter for API requests.

Implements token bucket algorithm with sliding window.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RateLimit:
    """Rate limit configuration."""
    max_requests: int
    window_seconds: float


@dataclass
class RateLimitStats:
    """Statistics for rate limiting."""
    total_requests: int = 0
    rejected_requests: int = 0
    waited_seconds: float = 0.0


class RateLimiter:
    """
    Token bucket rate limiter with sliding window.

    Args:
        max_requests: Maximum requests allowed per window
        window_seconds: Time window in seconds

    Example:
        >>> limiter = RateLimiter(max_requests=100, window_seconds=60)
        >>> limiter.wait_if_needed()
        >>> # Make API call
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: float = 60.0
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        self._lock = threading.Lock()
        self._requests: list = []
        self._stats = RateLimitStats()

    def is_allowed(self) -> bool:
        """
        Check if a request is allowed without waiting.

        Returns:
            True if request can proceed immediately
        """
        with self._lock:
            self._cleanup()

            if len(self._requests) >= self.max_requests:
                self._stats.rejected_requests += 1
                return False

            self._requests.append(time.time())
            self._stats.total_requests += 1
            return True

    def wait_if_needed(self) -> None:
        """
        Wait if rate limit would be exceeded.

        Blocks until a request can be made.
        """
        start_wait = time.time()

        with self._lock:
            self._cleanup()

            if len(self._requests) < self.max_requests:
                self._requests.append(time.time())
                self._stats.total_requests += 1
                return

            oldest = self._requests[0]
            wait_time = self.window_seconds - (time.time() - oldest)

            if wait_time > 0:
                time.sleep(wait_time)

        with self._lock:
            self._cleanup()
            self._requests.append(time.time())
            self._stats.total_requests += 1
            self._stats.waited_seconds += time.time() - start_wait

    def _cleanup(self) -> None:
        """Remove expired timestamps."""
        cutoff = time.time() - self.window_seconds
        self._requests = [t for t in self._requests if t > cutoff]

    def get_wait_time(self) -> float:
        """
        Get time to wait before next request.

        Returns:
            Seconds to wait, or 0 if can request now
        """
        with self._lock:
            self._cleanup()

            if len(self._requests) < self.max_requests:
                return 0.0

            oldest = self._requests[0]
            return max(0.0, self.window_seconds - (time.time() - oldest))

    def get_stats(self) -> RateLimitStats:
        """Get rate limiting statistics."""
        with self._lock:
            return RateLimitStats(
                total_requests=self._stats.total_requests,
                rejected_requests=self._stats.rejected_requests,
                waited_seconds=self._stats.waited_seconds
            )

    def reset(self) -> None:
        """Reset rate limiter state."""
        with self._lock:
            self._requests.clear()
            self._stats = RateLimitStats()


class MultiSourceRateLimiter:
    """
    Rate limiter managing multiple API sources.

    Args:
        limits: Dictionary of source names to RateLimit configs
    """

    def __init__(self, limits: Optional[Dict[str, RateLimit]] = None):
        if limits is None:
            limits = {
                "yahoo": RateLimit(max_requests=2000, window_seconds=3600),
                "alpaca": RateLimit(max_requests=200, window_seconds=60),
            }

        self._limiters: Dict[str, RateLimiter] = {
            source: RateLimiter(limit.max_requests, limit.window_seconds)
            for source, limit in limits.items()
        }

        self._default = RateLimiter()

    def wait_if_needed(self, source: str = "default") -> None:
        """Wait for rate limit for specific source."""
        limiter = self._limiters.get(source, self._default)
        limiter.wait_if_needed()

    def is_allowed(self, source: str = "default") -> bool:
        """Check if request is allowed for source."""
        limiter = self._limiters.get(source, self._default)
        return limiter.is_allowed()

    def get_stats(self, source: str = "default") -> RateLimitStats:
        """Get statistics for source."""
        limiter = self._limiters.get(source, self._default)
        return limiter.get_stats()
