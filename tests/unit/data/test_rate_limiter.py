"""
Unit tests for rate limiter.
"""

import pytest
import time
import threading

from trading_system.data.storage import RateLimiter, MultiSourceRateLimiter, RateLimit, RateLimitStats


class TestRateLimiter:
    """Tests for RateLimiter."""

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

    def test_is_allowed_tracks_rejected(self):
        """Test that rejected requests are tracked in stats."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        limiter.is_allowed()
        limiter.is_allowed()
        limiter.is_allowed()  # This should be rejected
        limiter.is_allowed()  # This should also be rejected
        
        stats = limiter.get_stats()
        assert stats.rejected_requests == 2

    def test_wait_if_needed(self):
        """Test that wait_if_needed blocks appropriately."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.5)
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        assert elapsed >= 0.4

    def test_wait_if_needed_with_room(self):
        """Test wait_if_needed when there's room under limit."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        # Should return immediately without waiting
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        assert elapsed < 0.1

    def test_window_reset(self):
        """Test that window resets after time period."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.2)
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        time.sleep(0.3)
        
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

    def test_get_stats_includes_wait_time(self):
        """Test that stats include waited time."""
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)
        
        limiter.wait_if_needed()  # First request
        limiter.wait_if_needed()  # Must wait
        
        stats = limiter.get_stats()
        
        assert stats.total_requests == 2
        assert stats.waited_seconds > 0

    def test_reset(self):
        """Test resetting the rate limiter."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            limiter.is_allowed()
        
        limiter.reset()
        
        assert limiter.is_allowed() is True

    def test_reset_clears_all_stats(self):
        """Test that reset clears all statistics."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        limiter.is_allowed()
        limiter.is_allowed()
        
        limiter.reset()
        
        stats = limiter.get_stats()
        assert stats.total_requests == 0
        assert stats.rejected_requests == 0

    def test_concurrent_access(self):
        """Test rate limiter with concurrent access."""
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        results = []
        
        def worker():
            limiter.wait_if_needed()
            results.append(True)
        
        threads = [threading.Thread(target=worker) for _ in range(20)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 20

    def test_concurrent_is_allowed(self):
        """Test is_allowed with concurrent access."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        results = []
        
        def worker():
            result = limiter.is_allowed()
            results.append(result)
        
        threads = [threading.Thread(target=worker) for _ in range(20)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should get some result (either True or False)
        assert len(results) == 20
        assert all(isinstance(r, bool) for r in results)

    def test_get_wait_time_no_wait_needed(self):
        """Test get_wait_time when no wait is needed."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        wait_time = limiter.get_wait_time()
        
        assert wait_time == 0.0

    def test_get_wait_time_at_limit(self):
        """Test get_wait_time when at limit."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.5)
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        wait_time = limiter.get_wait_time()
        
        assert 0 < wait_time <= 0.5

    def test_get_wait_time_under_limit(self):
        """Test get_wait_time when under limit."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        wait_time = limiter.get_wait_time()
        
        assert wait_time == 0.0

    def test_multiple_full_cycles(self):
        """Test multiple fill-and-drain cycles."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.2)
        
        # First cycle
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        time.sleep(0.3)
        
        # Second cycle - should be allowed again
        assert limiter.is_allowed() is True
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        time.sleep(0.3)
        
        # Third cycle
        assert limiter.is_allowed() is True

    def test_default_values(self):
        """Test default initialization values."""
        limiter = RateLimiter()
        
        assert limiter.max_requests == 100
        assert limiter.window_seconds == 60.0

    def test_zero_window(self):
        """Test rate limiter with zero window (not recommended but valid)."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.01)
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        time.sleep(0.02)
        
        # Window should have reset
        assert limiter.is_allowed() is True

    def test_large_max_requests(self):
        """Test rate limiter with large max_requests."""
        limiter = RateLimiter(max_requests=10000, window_seconds=60)
        
        # Should allow all requests
        for i in range(100):
            assert limiter.is_allowed() is True

    def test_very_small_window(self):
        """Test rate limiter with very small window."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.001)
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        time.sleep(0.01)
        
        # Window should have reset
        assert limiter.is_allowed() is True


class TestRateLimit:
    """Tests for RateLimit dataclass."""

    def test_rate_limit_creation(self):
        """Test creating a RateLimit."""
        limit = RateLimit(max_requests=100, window_seconds=60)
        
        assert limit.max_requests == 100
        assert limit.window_seconds == 60


class TestRateLimitStats:
    """Tests for RateLimitStats dataclass."""

    def test_default_values(self):
        """Test default values for RateLimitStats."""
        stats = RateLimitStats()
        
        assert stats.total_requests == 0
        assert stats.rejected_requests == 0
        assert stats.waited_seconds == 0.0

    def test_custom_values(self):
        """Test creating RateLimitStats with custom values."""
        stats = RateLimitStats(
            total_requests=100,
            rejected_requests=5,
            waited_seconds=10.5
        )
        
        assert stats.total_requests == 100
        assert stats.rejected_requests == 5
        assert stats.waited_seconds == 10.5


class TestMultiSourceRateLimiter:
    """Tests for MultiSourceRateLimiter."""

    def test_wait_for_source(self):
        """Test waiting for specific source."""
        limiter = MultiSourceRateLimiter({
            "yahoo": RateLimit(max_requests=100, window_seconds=60)
        })
        
        limiter.wait_if_needed("yahoo")
        assert limiter.is_allowed("yahoo") is True

    def test_default_source(self):
        """Test default source for unknown sources."""
        limiter = MultiSourceRateLimiter()
        
        limiter.wait_if_needed("unknown_source")
        assert limiter.is_allowed("unknown_source") is True

    def test_separate_limits_per_source(self):
        """Test that sources have separate limits."""
        limiter = MultiSourceRateLimiter({
            "source1": RateLimit(max_requests=2, window_seconds=60),
            "source2": RateLimit(max_requests=2, window_seconds=60)
        })
        
        limiter.wait_if_needed("source1")
        limiter.wait_if_needed("source1")
        
        limiter.wait_if_needed("source2")
        limiter.wait_if_needed("source2")
        
        assert limiter.is_allowed("source1") is False
        assert limiter.is_allowed("source2") is False

    def test_independent_source_limits(self):
        """Test that hitting one source limit doesn't affect another."""
        limiter = MultiSourceRateLimiter({
            "source1": RateLimit(max_requests=2, window_seconds=60),
            "source2": RateLimit(max_requests=5, window_seconds=60)
        })
        
        # Fill source1 to limit
        limiter.wait_if_needed("source1")
        limiter.wait_if_needed("source1")
        
        # source2 should still have room
        assert limiter.is_allowed("source1") is False
        assert limiter.is_allowed("source2") is True

    def test_get_stats_for_source(self):
        """Test getting stats for specific source."""
        limiter = MultiSourceRateLimiter({
            "yahoo": RateLimit(max_requests=100, window_seconds=60)
        })
        
        limiter.wait_if_needed("yahoo")
        limiter.wait_if_needed("yahoo")
        
        stats = limiter.get_stats("yahoo")
        
        assert stats.total_requests == 2

    def test_get_stats_for_unknown_source(self):
        """Test getting stats for unknown source uses default."""
        limiter = MultiSourceRateLimiter()
        
        limiter.wait_if_needed("unknown")
        
        stats = limiter.get_stats("unknown")
        
        assert stats.total_requests == 1

    def test_default_limits(self):
        """Test default limits are set correctly."""
        limiter = MultiSourceRateLimiter()
        
        # Should have default limiters for yahoo and alpaca
        assert limiter.is_allowed("yahoo") is True
        assert limiter.is_allowed("alpaca") is True

    def test_empty_limits_dict(self):
        """Test MultiSourceRateLimiter with empty limits dict."""
        limiter = MultiSourceRateLimiter(limits={})
        
        # Should fall back to default for all sources
        assert limiter.is_allowed("any_source") is True

    def test_multiple_sources_independent(self):
        """Test multiple sources operate independently."""
        limiter = MultiSourceRateLimiter({
            "source1": RateLimit(max_requests=1, window_seconds=60),
            "source2": RateLimit(max_requests=2, window_seconds=60)
        })
        
        # Use source1 twice to hit limit
        limiter.wait_if_needed("source1")
        limiter.wait_if_needed("source1")
        
        # source2 should still have room
        assert limiter.is_allowed("source1") is False
        assert limiter.is_allowed("source2") is True
        
        # Use source2 twice to hit limit
        limiter.wait_if_needed("source2")
        limiter.wait_if_needed("source2")
        
        # Now both should be at limit
        assert limiter.is_allowed("source1") is False
        assert limiter.is_allowed("source2") is False

    def test_concurrent_access_same_source(self):
        """Test concurrent access to same source."""
        limiter = MultiSourceRateLimiter({
            "shared": RateLimit(max_requests=50, window_seconds=60)
        })
        
        results = []
        
        def worker():
            limiter.wait_if_needed("shared")
            results.append(True)
        
        threads = [threading.Thread(target=worker) for _ in range(20)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 20

    def test_concurrent_access_different_sources(self):
        """Test concurrent access to different sources."""
        limiter = MultiSourceRateLimiter({
            "source1": RateLimit(max_requests=50, window_seconds=60),
            "source2": RateLimit(max_requests=50, window_seconds=60)
        })
        
        results1 = []
        results2 = []
        
        def worker1():
            limiter.wait_if_needed("source1")
            results1.append(True)
        
        def worker2():
            limiter.wait_if_needed("source2")
            results2.append(True)
        
        threads = [
            threading.Thread(target=worker1) for _ in range(10)
        ] + [
            threading.Thread(target=worker2) for _ in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results1) == 10
        assert len(results2) == 10


class TestRateLimiterEdgeCases:
    """Edge case tests for rate limiters."""

    def test_very_long_window(self):
        """Test rate limiter with very long window."""
        limiter = RateLimiter(max_requests=2, window_seconds=3600)  # 1 hour
        
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        # Should not be allowed after short wait
        assert limiter.is_allowed() is False
        
        # Wait time should be close to full window
        wait_time = limiter.get_wait_time()
        assert 3500 < wait_time <= 3600

    def test_thread_safety_on_stats(self):
        """Test thread safety when accessing stats during operations."""
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        
        def worker_and_check():
            limiter.wait_if_needed()
            limiter.get_stats()
        
        threads = [threading.Thread(target=worker_and_check) for _ in range(50)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without errors
        stats = limiter.get_stats()
        assert stats.total_requests == 50

    def test_duplicate_wait_calls(self):
        """Test multiple wait calls in sequence."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Make 5 requests
        for _ in range(5):
            limiter.wait_if_needed()
        
        # Next should wait and succeed
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        assert elapsed > 0

    def test_mixed_is_allowed_and_wait(self):
        """Test mixing is_allowed and wait_if_needed."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # First two with is_allowed
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is True
        
        # Third with wait_if_needed
        limiter.wait_if_needed()
        
        # Fourth should be rejected
        assert limiter.is_allowed() is False
