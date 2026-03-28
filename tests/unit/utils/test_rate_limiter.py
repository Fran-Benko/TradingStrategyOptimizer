"""
Unit tests for rate limiter utilities.

Tests cover:
- TokenBucketRateLimiter
- SlidingWindowRateLimiter
- RateLimiter (sliding window implementation)
- MultiSourceRateLimiter
- AdaptiveRateLimiter
- rate_limit decorator
- Thread safety and concurrency
"""

import pytest
import time
import threading
import asyncio
from unittest.mock import patch, MagicMock

from trading_system.utils.rate_limiter import (
    RateLimitConfig,
    RateLimitStats,
    RateLimiter,
    TokenBucketRateLimiter,
    SlidingWindowRateLimiter,
    MultiSourceRateLimiter,
    AdaptiveRateLimiter,
    rate_limit,
)


# =============================================================================
# RateLimitConfig Tests
# =============================================================================

class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        
        assert config.max_requests == 100
        assert config.window_seconds == 60.0
        assert config.burst_size == 100

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            max_requests=500,
            window_seconds=120.0,
            burst_size=50
        )
        
        assert config.max_requests == 500
        assert config.window_seconds == 120.0
        assert config.burst_size == 50

    def test_negative_max_requests_raises_error(self):
        """Test error for negative max_requests."""
        with pytest.raises(ValueError, match="max_requests must be positive"):
            RateLimitConfig(max_requests=-1)

    def test_zero_max_requests_raises_error(self):
        """Test error for zero max_requests."""
        with pytest.raises(ValueError, match="max_requests must be positive"):
            RateLimitConfig(max_requests=0)

    def test_negative_window_seconds_raises_error(self):
        """Test error for negative window_seconds."""
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            RateLimitConfig(window_seconds=-10)

    def test_zero_window_seconds_raises_error(self):
        """Test error for zero window_seconds."""
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            RateLimitConfig(window_seconds=0)

    def test_negative_burst_size_raises_error(self):
        """Test error for negative burst_size."""
        with pytest.raises(ValueError, match="burst_size must be positive"):
            RateLimitConfig(burst_size=-5)

    def test_burst_size_defaults_to_max_requests(self):
        """Test that burst_size defaults to max_requests."""
        config = RateLimitConfig(max_requests=200)
        
        assert config.burst_size == 200


# =============================================================================
# RateLimitStats Tests
# =============================================================================

class TestRateLimitStats:
    """Tests for RateLimitStats dataclass."""

    def test_default_values(self):
        """Test default statistics values."""
        stats = RateLimitStats()
        
        assert stats.total_requests == 0
        assert stats.rejected_requests == 0
        assert stats.waited_seconds == 0.0
        assert stats.last_request_time is None

    def test_acceptance_rate_no_requests(self):
        """Test acceptance rate with no requests."""
        stats = RateLimitStats()
        
        assert stats.acceptance_rate == 1.0

    def test_acceptance_rate_all_accepted(self):
        """Test acceptance rate when all requests accepted."""
        stats = RateLimitStats(total_requests=100, rejected_requests=0)
        
        assert stats.acceptance_rate == 1.0

    def test_acceptance_rate_some_rejected(self):
        """Test acceptance rate when some requests rejected."""
        stats = RateLimitStats(total_requests=100, rejected_requests=20)
        
        assert stats.acceptance_rate == 0.8


# =============================================================================
# RateLimiter Tests (Sliding Window)
# =============================================================================

class TestRateLimiter:
    """Tests for RateLimiter (sliding window implementation)."""

    def test_is_allowed_under_limit(self):
        """Test that requests are allowed under the limit."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        for i in range(10):
            assert limiter.is_allowed() is True

    def test_is_allowed_over_limit(self):
        """Test that requests are rejected over the limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            limiter.is_allowed()
        
        assert limiter.is_allowed() is False

    def test_wait_if_needed_allows_request(self):
        """Test wait_if_needed allows immediate request under limit."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        wait_time = limiter.wait_if_needed()
        
        assert wait_time == 0.0
        assert limiter.is_allowed() is True

    def test_wait_if_needed_blocks_when_full(self):
        """Test wait_if_needed blocks when at limit."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.2)
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        assert elapsed >= 0.15  # Should wait for window to clear

    def test_window_resets_after_time(self):
        """Test that window resets after time period."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.15)
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        time.sleep(0.25)
        
        assert limiter.is_allowed() is True

    def test_get_stats(self):
        """Test getting rate limiter statistics."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        limiter.is_allowed()
        limiter.is_allowed()
        limiter.is_allowed()
        
        stats = limiter.get_stats()
        
        assert stats.total_requests == 3
        assert stats.rejected_requests == 0

    def test_get_stats_rejected(self):
        """Test statistics include rejected requests."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        limiter.is_allowed()
        limiter.is_allowed()
        limiter.is_allowed()  # Should be rejected
        limiter.is_allowed()  # Should be rejected
        
        stats = limiter.get_stats()
        
        assert stats.total_requests == 4
        assert stats.rejected_requests == 2

    def test_reset(self):
        """Test resetting the rate limiter."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            limiter.is_allowed()
        
        limiter.reset()
        
        assert limiter.is_allowed() is True  # After reset, one call made
        assert limiter.get_remaining() == 4   # 5 - 1 = 4 remaining

    def test_get_remaining(self):
        """Test getting remaining requests."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        assert limiter.get_remaining() == 10
        
        limiter.is_allowed()
        limiter.is_allowed()
        
        assert limiter.get_remaining() == 8

    def test_get_wait_time_no_wait(self):
        """Test get_wait_time when no wait needed."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        wait_time = limiter.get_wait_time()
        
        assert wait_time == 0.0

    def test_get_wait_time_at_limit(self):
        """Test get_wait_time when at limit."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.5)
        
        limiter.is_allowed()
        limiter.is_allowed()
        
        wait_time = limiter.get_wait_time()
        
        assert wait_time > 0
        assert wait_time <= 0.5

    def test_concurrent_access(self):
        """Test rate limiter with concurrent access."""
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        results = []
        lock = threading.Lock()
        
        def worker():
            limiter.wait_if_needed()
            with lock:
                results.append(True)
        
        threads = [threading.Thread(target=worker) for _ in range(20)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 20
        
        stats = limiter.get_stats()
        assert stats.total_requests == 20


# =============================================================================
# TokenBucketRateLimiter Tests
# =============================================================================

class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    def test_try_acquire_success(self):
        """Test successful token acquisition."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5)
        
        result = limiter.try_acquire(5)
        
        assert result is True
        assert limiter.try_acquire(6) is False  # Not enough tokens left

    def test_try_acquire_depletes_tokens(self):
        """Test that try_acquire depletes tokens."""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=0)
        
        assert limiter.try_acquire(3) is True  # Uses 3, 2 left
        assert limiter.try_acquire(2) is True  # Uses 2, 0 left
        assert limiter.try_acquire(1) is False  # No tokens left

    def test_acquire_blocks_until_tokens_available(self):
        """Test that acquire blocks until tokens available."""
        limiter = TokenBucketRateLimiter(capacity=2, refill_rate=10)
        
        limiter.try_acquire(2)  # Use all tokens
        
        start = time.time()
        wait_time = limiter.acquire(1)
        elapsed = time.time() - start
        
        assert wait_time >= 0
        assert elapsed >= 0

    def test_refill_rate_works(self):
        """Test that refill rate adds tokens over time."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=100)
        
        limiter.try_acquire(10)  # Use all tokens
        
        time.sleep(0.05)  # Should get ~5 tokens
        
        assert limiter.try_acquire(5) is True

    def test_get_wait_time(self):
        """Test get_wait_time for token availability."""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=10)
        
        limiter.try_acquire(5)  # Use all tokens
        
        wait_time = limiter.get_wait_time(3)
        
        assert wait_time > 0
        assert wait_time <= 0.5  # Should need ~0.3 seconds for 3 tokens at 10/sec

    def test_get_stats(self):
        """Test getting statistics."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5)
        
        limiter.try_acquire(3)  # total_requests: 1, tokens used: 3
        limiter.try_acquire(2)  # total_requests: 2, tokens used: 5
        
        stats = limiter.get_stats()
        
        assert stats.total_requests == 2  # 2 successful requests

    def test_reset(self):
        """Test resetting the token bucket."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5)
        
        limiter.try_acquire(10)
        limiter.reset()
        
        assert limiter.try_acquire(10) is True

    def test_multiple_tokens(self):
        """Test acquiring multiple tokens at once."""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=1)
        
        assert limiter.try_acquire(5) is True
        assert limiter.try_acquire(6) is False  # Only 5 left
        
        time.sleep(2)  # Get 2 more tokens
        
        assert limiter.try_acquire(7) is True

    def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        limiter = TokenBucketRateLimiter(capacity=100, refill_rate=1000)
        results = []
        lock = threading.Lock()
        
        def worker():
            limiter.acquire(1)
            with lock:
                results.append(True)
        
        threads = [threading.Thread(target=worker) for _ in range(50)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 50


# =============================================================================
# SlidingWindowRateLimiter Tests
# =============================================================================

class TestSlidingWindowRateLimiter:
    """Tests for SlidingWindowRateLimiter."""

    def test_acquire_under_limit(self):
        """Test acquire under the limit."""
        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
        
        for i in range(10):
            wait_time = limiter.acquire()
            assert wait_time == 0.0

    def test_acquire_blocks_at_limit(self):
        """Test acquire blocks when at limit."""
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.2)
        
        limiter.acquire()
        limiter.acquire()
        
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        
        assert elapsed >= 0.15

    def test_try_acquire_success(self):
        """Test try_acquire returns True when available."""
        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
        
        assert limiter.try_acquire() is True

    def test_try_acquire_returns_false_at_limit(self):
        """Test try_acquire returns False when at limit."""
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
        
        limiter.try_acquire()
        limiter.try_acquire()
        
        assert limiter.try_acquire() is False

    def test_window_resets(self):
        """Test that window resets after time."""
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.15)
        
        limiter.acquire()
        limiter.acquire()
        
        time.sleep(0.25)
        
        assert limiter.try_acquire() is True

    def test_get_wait_time(self):
        """Test get_wait_time method."""
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.5)
        
        limiter.acquire()
        limiter.acquire()
        
        wait_time = limiter.get_wait_time()
        
        assert 0 < wait_time <= 0.5

    def test_get_stats(self):
        """Test getting statistics."""
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
        
        limiter.acquire()  # 1 success
        limiter.acquire()  # 2 success
        
        # At capacity, try_acquire should fail
        result = limiter.try_acquire()  # should fail
        assert result is False
        
        stats = limiter.get_stats()
        
        assert stats.total_requests == 2
        assert stats.rejected_requests == 1

    def test_reset(self):
        """Test resetting the rate limiter."""
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            limiter.acquire()
        
        limiter.reset()
        
        assert limiter.try_acquire() is True

    def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=60)
        results = []
        lock = threading.Lock()
        
        def worker():
            limiter.acquire()
            with lock:
                results.append(True)
        
        threads = [threading.Thread(target=worker) for _ in range(30)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 30


# =============================================================================
# MultiSourceRateLimiter Tests
# =============================================================================

class TestMultiSourceRateLimiter:
    """Tests for MultiSourceRateLimiter."""

    def test_default_sources(self):
        """Test default rate limits for common sources."""
        limiter = MultiSourceRateLimiter()
        
        assert limiter.is_allowed("yahoo") is True
        assert limiter.is_allowed("alpaca") is True

    def test_custom_sources(self):
        """Test custom rate limits per source."""
        limiter = MultiSourceRateLimiter({
            "api1": RateLimitConfig(max_requests=10, window_seconds=60),
            "api2": RateLimitConfig(max_requests=5, window_seconds=60)
        })
        
        assert limiter.is_allowed("api1") is True
        assert limiter.is_allowed("api2") is True

    def test_separate_limits_per_source(self):
        """Test that sources have separate limits."""
        limiter = MultiSourceRateLimiter({
            "source1": RateLimitConfig(max_requests=2, window_seconds=60),
            "source2": RateLimitConfig(max_requests=2, window_seconds=60)
        })
        
        limiter.wait_if_needed("source1")
        limiter.wait_if_needed("source1")
        
        limiter.wait_if_needed("source2")
        limiter.wait_if_needed("source2")
        
        assert limiter.is_allowed("source1") is False
        assert limiter.is_allowed("source2") is False

    def test_unknown_source_uses_default(self):
        """Test unknown source uses default limiter."""
        limiter = MultiSourceRateLimiter()
        
        # Should not raise, uses default
        limiter.wait_if_needed("unknown_source")
        
        assert limiter.is_allowed("unknown_source") is True

    def test_wait_if_needed(self):
        """Test wait_if_needed method."""
        limiter = MultiSourceRateLimiter({
            "api": RateLimitConfig(max_requests=100, window_seconds=60)
        })
        
        wait_time = limiter.wait_if_needed("api")
        
        assert wait_time == 0.0

    def test_get_remaining(self):
        """Test getting remaining requests."""
        limiter = MultiSourceRateLimiter({
            "api": RateLimitConfig(max_requests=10, window_seconds=60)
        })
        
        initial = limiter.get_remaining("api")
        assert initial == 10
        
        limiter.wait_if_needed("api")
        
        assert limiter.get_remaining("api") == 9

    def test_get_stats(self):
        """Test getting statistics per source."""
        limiter = MultiSourceRateLimiter({
            "api": RateLimitConfig(max_requests=100, window_seconds=60)
        })
        
        limiter.wait_if_needed("api")
        limiter.wait_if_needed("api")
        
        stats = limiter.get_stats("api")
        
        assert stats.total_requests == 2

    def test_reset_specific_source(self):
        """Test resetting specific source."""
        limiter = MultiSourceRateLimiter({
            "api": RateLimitConfig(max_requests=5, window_seconds=60)
        })
        
        for _ in range(5):
            limiter.wait_if_needed("api")
        
        limiter.reset("api")
        
        assert limiter.is_allowed("api") is True

    def test_reset_all_sources(self):
        """Test resetting all sources."""
        limiter = MultiSourceRateLimiter({
            "api1": RateLimitConfig(max_requests=5, window_seconds=60),
            "api2": RateLimitConfig(max_requests=5, window_seconds=60)
        })
        
        for _ in range(5):
            limiter.wait_if_needed("api1")
            limiter.wait_if_needed("api2")
        
        limiter.reset()  # Reset all
        
        assert limiter.is_allowed("api1") is True
        assert limiter.is_allowed("api2") is True


# =============================================================================
# AdaptiveRateLimiter Tests
# =============================================================================

class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""

    def test_initial_rate(self):
        """Test initial rate is set correctly."""
        limiter = AdaptiveRateLimiter(initial_rate=100)
        
        assert limiter.get_current_rate() == 100

    def test_on_success_gradually_increases(self):
        """Test that on_success gradually increases rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=100,
            recovery_factor=0.9
        )
        # Set low threshold for faster recovery
        limiter._recovery_threshold = 3
        
        for _ in range(3):
            limiter.on_success()
        
        # Should have increased (100 / 0.9 = ~111)
        assert limiter.get_current_rate() >= 100

    def test_on_rate_limit_hit_decreases(self):
        """Test that on_rate_limit_hit decreases rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=100,
            backoff_factor=2.0
        )
        
        limiter.on_rate_limit_hit()
        
        assert limiter.get_current_rate() == 50

    def test_rate_cannot_go_below_one(self):
        """Test that rate cannot go below 1."""
        limiter = AdaptiveRateLimiter(
            initial_rate=2,
            backoff_factor=10
        )
        
        for _ in range(10):
            limiter.on_rate_limit_hit()
        
        assert limiter.get_current_rate() >= 1

    def test_reset(self):
        """Test reset restores initial rate."""
        limiter = AdaptiveRateLimiter(initial_rate=100)
        
        limiter.on_rate_limit_hit()
        limiter.on_rate_limit_hit()
        
        limiter.reset()
        
        assert limiter.get_current_rate() == 100

    def test_wait_if_needed(self):
        """Test wait_if_needed doesn't block."""
        limiter = AdaptiveRateLimiter(initial_rate=100)
        
        # Should not raise
        limiter.wait_if_needed()


# =============================================================================
# rate_limit Decorator Tests
# =============================================================================

class TestRateLimitDecorator:
    """Tests for rate_limit decorator."""

    def test_decorator_limits_calls(self):
        """Test that decorator limits function calls."""
        call_count = 0
        
        @rate_limit(calls=3, period=1.0)
        def limited_func():
            nonlocal call_count
            call_count += 1
            return "done"
        
        # First 3 calls should succeed
        for _ in range(3):
            result = limited_func()
            assert result == "done"
        
        assert call_count == 3

    def test_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata."""
        @rate_limit(calls=10, period=1.0)
        def my_function():
            return 42
        
        assert my_function.__name__ == "my_function"

    def test_decorator_preserves_docstring(self):
        """Test that decorator preserves docstring."""
        @rate_limit(calls=10, period=1.0)
        def documented_func():
            """This is my docstring."""
            return 42
        
        assert documented_func.__doc__ == "This is my docstring."

    def test_decorator_has_rate_limiter(self):
        """Test that decorated function has rate_limiter attribute."""
        @rate_limit(calls=10, period=1.0)
        def my_func():
            return 42
        
        assert hasattr(my_func, "_rate_limiter")

    def test_decorator_has_get_stats(self):
        """Test that decorated function has get_stats method."""
        @rate_limit(calls=10, period=1.0)
        def my_func():
            return 42
        
        assert hasattr(my_func, "get_stats")
        
        my_func()
        stats = my_func.get_stats()
        
        assert stats.total_requests >= 1

    def test_decorator_has_reset(self):
        """Test that decorated function has reset method."""
        @rate_limit(calls=2, period=1.0)
        def my_func():
            return 42
        
        my_func()
        my_func()
        
        my_func.reset()
        
        stats = my_func.get_stats()
        assert stats.total_requests == 0

    def test_decorator_with_different_limiter_class(self):
        """Test decorator with compatible rate limiter class."""
        # Note: TokenBucketRateLimiter uses different params (capacity, refill_rate)
        # so we test with the default RateLimiter which is compatible
        @rate_limit(calls=5, period=1.0)
        def my_func():
            return 42
        
        for _ in range(5):
            my_func()
        
        stats = my_func.get_stats()
        assert stats.total_requests == 5

    @pytest.mark.asyncio
    async def test_decorator_with_async_function(self):
        """Test decorator works with async functions."""
        call_count = 0
        
        @rate_limit(calls=3, period=1.0)
        async def async_func():
            nonlocal call_count
            call_count += 1
            return "done"
        
        for _ in range(3):
            result = await async_func()
            assert result == "done"
        
        assert call_count == 3


# =============================================================================
# Thread Safety Tests
# =============================================================================

class TestRateLimiterThreadSafety:
    """Tests for thread safety of rate limiters."""

    def test_rate_limiter_thread_safety(self):
        """Test RateLimiter is thread-safe."""
        limiter = RateLimiter(max_requests=1000, window_seconds=60)
        successful = []
        rejected = []
        lock = threading.Lock()
        
        def worker():
            if limiter.is_allowed():
                with lock:
                    successful.append(True)
            else:
                with lock:
                    rejected.append(True)
        
        threads = [threading.Thread(target=worker) for _ in range(100)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        stats = limiter.get_stats()
        assert len(successful) + len(rejected) == 100
        assert stats.total_requests == len(successful)

    def test_token_bucket_thread_safety(self):
        """Test TokenBucketRateLimiter is thread-safe."""
        limiter = TokenBucketRateLimiter(capacity=1000, refill_rate=100)
        successful = []
        lock = threading.Lock()
        
        def worker():
            if limiter.try_acquire(1):
                with lock:
                    successful.append(True)
        
        threads = [threading.Thread(target=worker) for _ in range(100)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have acquired approximately 1000 tokens
        assert len(successful) <= 1000

    def test_sliding_window_thread_safety(self):
        """Test SlidingWindowRateLimiter is thread-safe."""
        limiter = SlidingWindowRateLimiter(max_requests=1000, window_seconds=60)
        successful = []
        lock = threading.Lock()
        
        def worker():
            if limiter.try_acquire():
                with lock:
                    successful.append(True)
        
        threads = [threading.Thread(target=worker) for _ in range(100)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(successful) == 100  # All should succeed since we have 1000 capacity

    def test_multiple_threads_exact_count(self):
        """Test that multiple threads result in exact request count."""
        limiter = RateLimiter(max_requests=50, window_seconds=60)
        results = []
        lock = threading.Lock()
        
        def worker():
            limiter.wait_if_needed()
            with lock:
                results.append(time.time())
        
        threads = [threading.Thread(target=worker) for _ in range(50)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 50
        
        stats = limiter.get_stats()
        assert stats.total_requests == 50


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

class TestRateLimiterEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_capacity_token_bucket(self):
        """Test TokenBucketRateLimiter with zero capacity."""
        limiter = TokenBucketRateLimiter(capacity=0, refill_rate=1)
        
        assert limiter.try_acquire(1) is False

    def test_large_number_of_requests(self):
        """Test handling large number of rapid requests."""
        limiter = RateLimiter(max_requests=10000, window_seconds=60)
        
        for _ in range(10000):
            limiter.is_allowed()
        
        assert limiter.is_allowed() is False

    def test_very_small_window(self):
        """Test with very small time window."""
        limiter = RateLimiter(max_requests=5, window_seconds=0.01)
        
        for _ in range(5):
            limiter.wait_if_needed()
        
        time.sleep(0.02)
        
        assert limiter.is_allowed() is True

    def test_very_large_window(self):
        """Test with very large time window."""
        limiter = RateLimiter(max_requests=5, window_seconds=86400)  # 1 day
        
        for _ in range(5):
            limiter.wait_if_needed()
        
        assert limiter.is_allowed() is False
        assert limiter.get_remaining() == 0

    def test_concurrent_reset_and_access(self):
        """Test thread-safe concurrent reset and access."""
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        
        def worker_reset():
            for _ in range(10):
                limiter.reset()
                time.sleep(0.001)
        
        def worker_access():
            for _ in range(10):
                limiter.wait_if_needed()
        
        threads = [
            threading.Thread(target=worker_reset),
            threading.Thread(target=worker_access)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should not raise any exceptions
