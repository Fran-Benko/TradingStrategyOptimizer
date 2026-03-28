"""
Rate limiting utilities for the trading system.

Provides multiple rate limiting algorithms:
- Token bucket algorithm with configurable refill rates
- Sliding window rate limiter for smooth rate limiting
- Decorator for easy function rate limiting
- Multi-source rate limiter for managing multiple API sources

All implementations are thread-safe for concurrent use.
"""

import asyncio
import functools
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple, Union


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    max_requests: int = 100
    window_seconds: float = 60.0
    burst_size: Optional[int] = None
    
    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.burst_size is None:
            self.burst_size = self.max_requests
        elif self.burst_size <= 0:
            raise ValueError("burst_size must be positive")


@dataclass
class RateLimitStats:
    """Statistics for rate limiting operations."""
    
    total_requests: int = 0
    rejected_requests: int = 0
    waited_seconds: float = 0.0
    last_request_time: Optional[float] = None
    
    @property
    def acceptance_rate(self) -> float:
        """Calculate the acceptance rate."""
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.rejected_requests) / self.total_requests


class RateLimiter:
    """
    Token bucket rate limiter with sliding window.
    
    Uses a sliding window algorithm to track request timestamps,
    ensuring requests are evenly distributed within the time window.
    
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
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        
        self._lock = threading.RLock()
        self._requests: list[float] = []
        self._stats = RateLimitStats()
    
    def is_allowed(self) -> bool:
        """
        Check if a request is allowed without waiting.
        
        Returns:
            True if request can proceed immediately
        """
        with self._lock:
            self._cleanup()
            self._stats.total_requests += 1
            
            if len(self._requests) >= self.max_requests:
                self._stats.rejected_requests += 1
                return False
            
            self._requests.append(time.time())
            self._stats.last_request_time = time.time()
            return True
    
    def wait_if_needed(self) -> float:
        """
        Wait if rate limit would be exceeded.
        
        Blocks until a request can be made.
        
        Returns:
            Time waited in seconds
        """
        start_wait = time.time()
        
        with self._lock:
            self._cleanup()
            
            if len(self._requests) < self.max_requests:
                self._requests.append(time.time())
                self._stats.total_requests += 1
                self._stats.last_request_time = time.time()
                return 0.0
            
            oldest = self._requests[0]
            wait_time = self.window_seconds - (time.time() - oldest)
        
        if wait_time > 0:
            time.sleep(wait_time)
        
        with self._lock:
            self._cleanup()
            self._requests.append(time.time())
            self._stats.total_requests += 1
            self._stats.last_request_time = time.time()
            waited = time.time() - start_wait
            self._stats.waited_seconds += waited
            return waited
    
    async def wait_if_needed_async(self) -> float:
        """
        Async version of wait_if_needed.
        
        Returns:
            Time waited in seconds
        """
        start_wait = time.time()
        
        with self._lock:
            self._cleanup()
            
            if len(self._requests) < self.max_requests:
                self._requests.append(time.time())
                self._stats.total_requests += 1
                self._stats.last_request_time = time.time()
                return 0.0
            
            oldest = self._requests[0]
            wait_time = self.window_seconds - (time.time() - oldest)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        with self._lock:
            self._cleanup()
            self._requests.append(time.time())
            self._stats.total_requests += 1
            self._stats.last_request_time = time.time()
            waited = time.time() - start_wait
            self._stats.waited_seconds += waited
            return waited
    
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
                waited_seconds=self._stats.waited_seconds,
                last_request_time=self._stats.last_request_time
            )
    
    def reset(self) -> None:
        """Reset rate limiter state."""
        with self._lock:
            self._requests.clear()
            self._stats = RateLimitStats()
    
    def get_remaining(self) -> int:
        """
        Get number of remaining requests in current window.
        
        Returns:
            Number of requests that can be made without waiting
        """
        with self._lock:
            self._cleanup()
            return max(0, self.max_requests - len(self._requests))


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter with configurable refill rates.
    
    The token bucket algorithm allows burst traffic up to the bucket size,
    while enforcing an average rate limit over time.
    
    Args:
        capacity: Maximum tokens (burst size)
        refill_rate: Tokens added per second
        
    Example:
        >>> limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5)
        >>> if limiter.try_acquire():
        ...     make_request()
    """
    
    def __init__(
        self,
        capacity: int = 100,
        refill_rate: float = 10.0
    ) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        
        self._lock = threading.RLock()
        self._tokens = float(capacity)
        self._last_refill = time.time()
        self._stats = RateLimitStats()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        
        tokens_to_add = elapsed * self.refill_rate
        self._tokens = min(self.capacity, self._tokens + tokens_to_add)
        self._last_refill = now
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._stats.total_requests += 1
                self._stats.last_request_time = time.time()
                return True
            
            self._stats.rejected_requests += 1
            return False
    
    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, blocking until available.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        start_wait = time.time()
        
        while True:
            with self._lock:
                self._refill()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    self._stats.total_requests += 1
                    self._stats.last_request_time = time.time()
                    waited = time.time() - start_wait
                    self._stats.waited_seconds += waited
                    return waited
                
                # Calculate wait time for needed tokens
                needed = tokens - self._tokens
                wait_time = needed / self.refill_rate
            
            time.sleep(min(wait_time, 0.1))  # Sleep in small increments
    
    async def acquire_async(self, tokens: int = 1) -> float:
        """
        Async version of acquire.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        start_wait = time.time()
        
        while True:
            with self._lock:
                self._refill()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    self._stats.total_requests += 1
                    self._stats.last_request_time = time.time()
                    waited = time.time() - start_wait
                    self._stats.waited_seconds += waited
                    return waited
                
                needed = tokens - self._tokens
                wait_time = needed / self.refill_rate
            
            await asyncio.sleep(min(wait_time, 0.1))
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time until specified tokens are available.
        
        Args:
            tokens: Number of tokens to check
            
        Returns:
            Seconds to wait, or 0 if available now
        """
        with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                return 0.0
            
            needed = tokens - self._tokens
            return needed / self.refill_rate
    
    def get_stats(self) -> RateLimitStats:
        """Get rate limiting statistics."""
        with self._lock:
            self._refill()
            return RateLimitStats(
                total_requests=self._stats.total_requests,
                rejected_requests=self._stats.rejected_requests,
                waited_seconds=self._stats.waited_seconds,
                last_request_time=self._stats.last_request_time
            )
    
    def reset(self) -> None:
        """Reset the token bucket."""
        with self._lock:
            self._tokens = float(self.capacity)
            self._last_refill = time.time()
            self._stats = RateLimitStats()


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter with precise request tracking.
    
    Uses a more accurate sliding window algorithm that weights requests
    by their position in the window, providing smoother rate limiting.
    
    Args:
        max_requests: Maximum requests per window
        window_seconds: Window size in seconds
        
    Example:
        >>> limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=60)
        >>> limiter.acquire()
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: float = 60.0
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        
        self._lock = threading.RLock()
        self._timestamps: list[float] = []
        self._stats = RateLimitStats()
    
    def acquire(self) -> float:
        """
        Acquire a slot in the rate limiter, blocking if necessary.
        
        Returns:
            Time waited in seconds
        """
        start_wait = time.time()
        
        with self._lock:
            self._cleanup()
            
            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(time.time())
                self._stats.total_requests += 1
                self._stats.last_request_time = time.time()
                return 0.0
        
        # Wait for oldest request to expire
        with self._lock:
            oldest = self._timestamps[0] if self._timestamps else time.time()
            wait_time = max(0.0, self.window_seconds - (time.time() - oldest))
        
        if wait_time > 0:
            time.sleep(wait_time)
        
        with self._lock:
            self._cleanup()
            self._timestamps.append(time.time())
            self._stats.total_requests += 1
            self._stats.last_request_time = time.time()
            waited = time.time() - start_wait
            self._stats.waited_seconds += waited
            return waited
    
    async def acquire_async(self) -> float:
        """Async version of acquire."""
        start_wait = time.time()
        
        with self._lock:
            self._cleanup()
            
            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(time.time())
                self._stats.total_requests += 1
                self._stats.last_request_time = time.time()
                return 0.0
        
        with self._lock:
            oldest = self._timestamps[0] if self._timestamps else time.time()
            wait_time = max(0.0, self.window_seconds - (time.time() - oldest))
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        with self._lock:
            self._cleanup()
            self._timestamps.append(time.time())
            self._stats.total_requests += 1
            self._stats.last_request_time = time.time()
            waited = time.time() - start_wait
            self._stats.waited_seconds += waited
            return waited
    
    def try_acquire(self) -> bool:
        """
        Try to acquire without blocking.
        
        Returns:
            True if acquired, False otherwise
        """
        with self._lock:
            self._cleanup()
            
            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(time.time())
                self._stats.total_requests += 1
                self._stats.last_request_time = time.time()
                return True
            
            self._stats.rejected_requests += 1
            return False
    
    def _cleanup(self) -> None:
        """Remove expired timestamps."""
        cutoff = time.time() - self.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]
    
    def get_wait_time(self) -> float:
        """
        Get time until next request can be made.
        
        Returns:
            Seconds to wait, or 0 if can request now
        """
        with self._lock:
            self._cleanup()
            
            if len(self._timestamps) < self.max_requests:
                return 0.0
            
            oldest = self._timestamps[0]
            return max(0.0, self.window_seconds - (time.time() - oldest))
    
    def get_stats(self) -> RateLimitStats:
        """Get rate limiting statistics."""
        with self._lock:
            return RateLimitStats(
                total_requests=self._stats.total_requests,
                rejected_requests=self._stats.rejected_requests,
                waited_seconds=self._stats.waited_seconds,
                last_request_time=self._stats.last_request_time
            )
    
    def reset(self) -> None:
        """Reset the rate limiter."""
        with self._lock:
            self._timestamps.clear()
            self._stats = RateLimitStats()


class MultiSourceRateLimiter:
    """
    Rate limiter managing multiple API sources.
    
    Centralizes rate limiting for multiple data sources with different
    rate limits, allowing independent control per source.
    
    Args:
        limits: Dictionary of source names to RateLimitConfig
        
    Example:
        >>> limiter = MultiSourceRateLimiter({
        ...     "yahoo": RateLimitConfig(max_requests=2000, window_seconds=3600),
        ...     "alpaca": RateLimitConfig(max_requests=200, window_seconds=60),
        ... })
        >>> limiter.wait_if_needed("alpaca")
    """
    
    def __init__(
        self,
        limits: Optional[Dict[str, RateLimitConfig]] = None
    ) -> None:
        if limits is None:
            limits = {
                "yahoo": RateLimitConfig(max_requests=2000, window_seconds=3600),
                "alpaca": RateLimitConfig(max_requests=200, window_seconds=60),
            }
        
        self._limiters: Dict[str, RateLimiter] = {
            source: RateLimiter(config.max_requests, config.window_seconds)
            for source, config in limits.items()
        }
        
        self._default = RateLimiter()
    
    def wait_if_needed(self, source: str = "default") -> float:
        """
        Wait for rate limit for specific source.
        
        Args:
            source: The source identifier
            
        Returns:
            Time waited in seconds
        """
        limiter = self._limiters.get(source, self._default)
        return limiter.wait_if_needed()
    
    def is_allowed(self, source: str = "default") -> bool:
        """
        Check if request is allowed for source.
        
        Args:
            source: The source identifier
            
        Returns:
            True if request is allowed
        """
        limiter = self._limiters.get(source, self._default)
        return limiter.is_allowed()
    
    def get_wait_time(self, source: str = "default") -> float:
        """
        Get wait time for source.
        
        Args:
            source: The source identifier
            
        Returns:
            Seconds to wait
        """
        limiter = self._limiters.get(source, self._default)
        return limiter.get_wait_time()
    
    def get_remaining(self, source: str = "default") -> int:
        """
        Get remaining requests for source.
        
        Args:
            source: The source identifier
            
        Returns:
            Number of remaining requests
        """
        limiter = self._limiters.get(source, self._default)
        return limiter.get_remaining()
    
    def get_stats(self, source: str = "default") -> RateLimitStats:
        """
        Get statistics for source.
        
        Args:
            source: The source identifier
            
        Returns:
            Rate limiting statistics
        """
        limiter = self._limiters.get(source, self._default)
        return limiter.get_stats()
    
    def reset(self, source: Optional[str] = None) -> None:
        """
        Reset rate limiter(s).
        
        Args:
            source: Specific source to reset, or None for all
        """
        if source:
            limiter = self._limiters.get(source, self._default)
            limiter.reset()
        else:
            for limiter in self._limiters.values():
                limiter.reset()
            self._default.reset()


# Decorator for easy function rate limiting
def rate_limit(
    calls: int = 10,
    period: float = 1.0,
    limiter_class: type = RateLimiter
) -> Callable:
    """
    Decorator for rate limiting a function.
    
    Wraps a function to enforce rate limiting on its calls.
    
    Args:
        calls: Maximum number of calls per period
        period: Time period in seconds
        limiter_class: Rate limiter class to use
        
    Returns:
        Decorated function
        
    Example:
        >>> @rate_limit(calls=10, period=1.0)
        ... def fetch_data(symbol):
        ...     return api.get(symbol)
    """
    limiter = limiter_class(max_requests=calls, window_seconds=period)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait_if_needed()
            return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            await limiter.wait_if_needed_async()
            return await func(*args, **kwargs)
        
        # Attach limiter and stats to wrapper for inspection
        wrapper._rate_limiter = limiter
        wrapper.get_stats = limiter.get_stats
        wrapper.reset = limiter.reset
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


class AdaptiveRateLimiter:
    """
    Rate limiter that adapts to API responses.
    
    Automatically adjusts rate limits based on 429 (Too Many Requests)
    responses from APIs, providing graceful degradation.
    
    Args:
        initial_rate: Initial max requests per window
        window_seconds: Window size in seconds
        backoff_factor: Factor to multiply wait time on rate limit hit
        recovery_factor: Factor to reduce wait time on successful requests
        
    Example:
        >>> limiter = AdaptiveRateLimiter(initial_rate=100)
        >>> try:
        ...     response = make_request()
        ... except RateLimitHit:
        ...     limiter.on_rate_limit_hit()
    """
    
    def __init__(
        self,
        initial_rate: int = 100,
        window_seconds: float = 60.0,
        backoff_factor: float = 2.0,
        recovery_factor: float = 0.95
    ) -> None:
        self.current_rate = initial_rate
        self.window_seconds = window_seconds
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        
        self._base_rate = initial_rate
        self._lock = threading.RLock()
        self._limiter = RateLimiter(initial_rate, window_seconds)
        self._consecutive_successes = 0
        self._recovery_threshold = 10
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        self._limiter.wait_if_needed()
    
    def on_success(self) -> None:
        """Call when a request succeeds - gradually increases rate."""
        with self._lock:
            self._consecutive_successes += 1
            
            if self._consecutive_successes >= self._recovery_threshold:
                new_rate = int(self.current_rate / self.recovery_factor)
                if new_rate > self._base_rate:
                    new_rate = self._base_rate
                
                if new_rate != self.current_rate:
                    self.current_rate = new_rate
                    self._limiter = RateLimiter(new_rate, self.window_seconds)
                
                self._consecutive_successes = 0
    
    def on_rate_limit_hit(self) -> None:
        """Call when a 429 response is received - decreases rate."""
        with self._lock:
            self.current_rate = max(1, int(self.current_rate / self.backoff_factor))
            self._limiter = RateLimiter(self.current_rate, self.window_seconds)
            self._consecutive_successes = 0
    
    def get_current_rate(self) -> int:
        """Get the current effective rate."""
        return self.current_rate
    
    def reset(self) -> None:
        """Reset to initial rate."""
        with self._lock:
            self.current_rate = self._base_rate
            self._limiter = RateLimiter(self._base_rate, self.window_seconds)
            self._consecutive_successes = 0
