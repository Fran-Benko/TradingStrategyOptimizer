"""
Cache manager for data storage.

Provides in-memory and file-based caching for fetched data.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd


class CacheManager:
    """
    Cache manager with in-memory and optional disk persistence.

    Args:
        ttl: Time-to-live for cache entries in seconds
        max_size: Maximum number of entries
        persist_path: Optional path for disk persistence
    """

    def __init__(
        self,
        ttl: int = 3600,
        max_size: int = 1000,
        persist_path: Optional[str] = None
    ):
        self.ttl = ttl
        self.max_size = max_size
        self.persist_path = persist_path

        self._cache: dict = {}
        self._timestamps: dict = {}
        self._access_times: dict = {}

        if persist_path:
            self._persist_dir = Path(persist_path)
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None

        if self._is_expired(key):
            self._remove(key)
            return None

        self._access_times[key] = datetime.now()
        return self._cache[key]

    def set(self, key: str, value: pd.DataFrame) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: DataFrame to cache
        """
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        self._cache[key] = value.copy()
        self._timestamps[key] = datetime.now()
        self._access_times[key] = datetime.now()

        if self.persist_path:
            self._save_to_disk(key, value)

    def _is_expired(self, key: str) -> bool:
        """Check if entry is expired."""
        if key not in self._timestamps:
            return True

        age = datetime.now() - self._timestamps[key]
        return age.total_seconds() > self.ttl

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_times:
            return

        lru_key = min(self._access_times, key=self._access_times.get)
        self._remove(lru_key)

    def _remove(self, key: str) -> None:
        """Remove entry from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        self._access_times.pop(key, None)

        if self.persist_path:
            self._remove_from_disk(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()
        self._access_times.clear()

        if self.persist_path:
            for f in self._persist_dir.glob("*.parquet"):
                f.unlink()

    def _save_to_disk(self, key: str, value: pd.DataFrame) -> None:
        """Save cache entry to disk."""
        safe_key = key.replace(":", "_").replace("/", "_")
        path = self._persist_dir / f"{safe_key}.parquet"

        try:
            value.to_parquet(path)
        except Exception:
            pass

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        if not self._persist_dir.exists():
            return

        for path in self._persist_dir.glob("*.parquet"):
            try:
                key = path.stem.replace("_", ":")
                df = pd.read_parquet(path)
                self._cache[key] = df
                self._timestamps[key] = datetime.fromtimestamp(path.stat().st_mtime)
                self._access_times[key] = datetime.now()
            except Exception:
                pass

    def _remove_from_disk(self, key: str) -> None:
        """Remove cache entry from disk."""
        safe_key = key.replace(":", "_").replace("/", "_")
        path = self._persist_dir / f"{safe_key}.parquet"

        if path.exists():
            path.unlink()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = sum(1 for k in self._cache if self._is_expired(k))

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl,
            "persisted": self.persist_path is not None
        }


class InMemoryCache:
    """
    Simple in-memory LRU cache for DataFrames.
    """

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: dict = {}
        self._order: list = []

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """Get value from cache."""
        if key not in self._cache:
            return None

        self._order.remove(key)
        self._order.append(key)

        return self._cache[key]

    def set(self, key: str, value: pd.DataFrame) -> None:
        """Set value in cache."""
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self.max_size:
            oldest = self._order.pop(0)
            del self._cache[oldest]

        self._cache[key] = value.copy()
        self._order.append(key)

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()
        self._order.clear()
