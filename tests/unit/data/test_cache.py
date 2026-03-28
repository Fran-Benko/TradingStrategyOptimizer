"""
Unit tests for cache manager.
"""

import pytest
import pandas as pd
import time
from datetime import datetime

from trading_system.data.storage import CacheManager, InMemoryCache


class TestInMemoryCache:
    """Tests for InMemoryCache."""

    def test_get_returns_none_for_missing_key(self):
        """Test that get returns None for non-existent key."""
        cache = InMemoryCache()
        assert cache.get("missing") is None

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = InMemoryCache()
        data = pd.DataFrame({"a": [1, 2, 3]})
        
        cache.set("test", data)
        result = cache.get("test")
        
        assert result is not None
        assert result.equals(data)

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = InMemoryCache(max_size=3)
        
        cache.set("a", pd.DataFrame({"a": [1]}))
        cache.set("b", pd.DataFrame({"b": [2]}))
        cache.set("c", pd.DataFrame({"c": [3]}))
        
        cache.get("a")
        cache.set("d", pd.DataFrame({"d": [4]}))
        
        assert cache.get("b") is None
        assert cache.get("a") is not None

    def test_clear(self):
        """Test cache clearing."""
        cache = InMemoryCache()
        
        cache.set("a", pd.DataFrame({"a": [1]}))
        cache.set("b", pd.DataFrame({"b": [2]}))
        
        cache.clear()
        
        assert cache.get("a") is None
        assert cache.get("b") is None


class TestCacheManager:
    """Tests for CacheManager."""

    def test_get_returns_none_for_missing_key(self):
        """Test that get returns None for non-existent key."""
        cache = CacheManager()
        assert cache.get("missing") is None

    def test_set_and_get_with_ttl(self):
        """Test set and get with TTL."""
        cache = CacheManager(ttl=1)
        data = pd.DataFrame({"a": [1, 2, 3]})
        
        cache.set("test", data)
        result = cache.get("test")
        
        assert result is not None
        assert result.equals(data)

    def test_expiration(self):
        """Test that entries expire after TTL."""
        cache = CacheManager(ttl=1)
        data = pd.DataFrame({"a": [1, 2, 3]})
        
        cache.set("test", data)
        time.sleep(1.1)
        
        assert cache.get("test") is None

    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = CacheManager(max_size=100, ttl=3600)
        
        cache.set("a", pd.DataFrame({"a": [1]}))
        cache.set("b", pd.DataFrame({"b": [2]}))
        
        stats = cache.get_stats()
        
        assert stats["total_entries"] == 2
        assert stats["max_size"] == 100
        assert stats["ttl_seconds"] == 3600

    def test_max_size_eviction(self):
        """Test that entries are evicted when max size is reached."""
        cache = CacheManager(max_size=2)
        
        cache.set("a", pd.DataFrame({"a": [1]}))
        cache.set("b", pd.DataFrame({"b": [2]}))
        cache.set("c", pd.DataFrame({"c": [3]}))
        
        assert cache.get("a") is None
        assert cache.get("c") is not None
