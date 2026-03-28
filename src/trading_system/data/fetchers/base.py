"""
Base data fetcher classes and protocols.

Provides abstract interfaces for data fetching from various sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataFetcher(Protocol):
    """Protocol for data fetcher implementations."""

    def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol."""
        ...

    def fetch_batch(
        self,
        symbols: List[str],
        start: str,
        end: str,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols."""
        ...


@dataclass
class FetchResult:
    """Result from a data fetch operation."""

    symbol: str
    data: pd.DataFrame
    source: str
    fetched_at: datetime
    cached: bool = False
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if fetch was successful."""
        return self.error is None and not self.data.empty

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "rows": len(self.data),
            "source": self.source,
            "fetched_at": self.fetched_at.isoformat(),
            "cached": self.cached,
            "error": self.error
        }


class BaseDataFetcher(ABC):
    """
    Abstract base class for data fetchers.

    Provides common functionality for caching, rate limiting,
    and error handling.

    Args:
        cache: Optional cache instance for storing fetched data
        rate_limiter: Optional rate limiter for API calls
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        cache: Optional[Any] = None,
        rate_limiter: Optional[Any] = None,
        timeout: int = 30
    ):
        self.cache = cache
        self.rate_limiter = rate_limiter
        self.timeout = timeout
        self._session = None

    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._setup_session(self._session)
        return self._session

    def _setup_session(self, session):
        """Setup session with headers, auth, etc. Override in subclass."""
        pass

    def _get_cache_key(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str
    ) -> str:
        """Generate cache key for a fetch operation."""
        return f"{self.source_name}:{symbol}:{start}:{end}:{interval}"

    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get data from cache if available."""
        if self.cache is None:
            return None
        return self.cache.get(cache_key)

    def _save_to_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """Save data to cache."""
        if self.cache is not None:
            self.cache.set(cache_key, data)

    def _wait_for_rate_limit(self) -> None:
        """Wait if rate limit is in effect."""
        if self.rate_limiter is not None:
            self.rate_limiter.wait_if_needed()

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the data source."""
        pass

    def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format
            interval: Data interval (1d, 1h, 5m, etc.)

        Returns:
            DataFrame with columns: open, high, low, close, volume

        Raises:
            DataFetchError: If fetch fails
        """
        from trading_system.exceptions import DataFetchError

        cache_key = self._get_cache_key(symbol, start, end, interval)

        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

        self._wait_for_rate_limit()

        try:
            data = self._fetch_from_api(symbol, start, end, interval)
            data = self._validate_and_normalize(data, symbol)
            self._save_to_cache(cache_key, data)
            return data

        except Exception as e:
            raise DataFetchError(
                f"Failed to fetch {symbol} from {self.source_name}: {e}"
            ) from e

    def fetch_batch(
        self,
        symbols: List[str],
        start: str,
        end: str,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols.

        Args:
            symbols: List of stock symbols
            start: Start date
            end: End date
            interval: Data interval

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        from trading_system.exceptions import DataFetchError

        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.fetch(symbol, start, end, interval)
            except DataFetchError as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to fetch {symbol}: {e}")
                results[symbol] = pd.DataFrame()

        return results

    @abstractmethod
    def _fetch_from_api(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str
    ) -> pd.DataFrame:
        """Fetch data from the API. Must be implemented by subclasses."""
        pass

    def _validate_and_normalize(
        self,
        data: pd.DataFrame,
        symbol: str
    ) -> pd.DataFrame:
        """
        Validate and normalize fetched data.

        Args:
            data: Raw data from API
            symbol: Symbol for validation

        Returns:
            Normalized DataFrame
        """
        required_columns = ["open", "high", "low", "close", "volume"]
        missing = set(required_columns) - set(data.columns)
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        data = data[required_columns].copy()

        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)

        data.index.name = "date"

        data = data.sort_index()

        invalid = (data["high"] < data["low"]) | (data["close"] > data["high"]) | (data["close"] < data["low"])
        if invalid.any():
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid OHLC data for {symbol}, fixing...")
            data = self._fix_ohlc_errors(data)

        return data

    def _fix_ohlc_errors(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fix common OHLC errors."""
        data = data.copy()

        data["high"] = data[["open", "high", "low", "close"]].max(axis=1)
        data["low"] = data[["open", "high", "low", "close"]].min(axis=1)

        return data
