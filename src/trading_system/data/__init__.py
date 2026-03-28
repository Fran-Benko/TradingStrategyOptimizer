"""
Data module.

Provides data fetching, caching, and validation.
"""

from trading_system.data.fetchers import (
    BaseDataFetcher,
    DataFetcher,
    FetchResult,
    YahooDataFetcher,
    AlpacaDataFetcher,
    GoogleFinanceFetcher,
    MockDataFetcher,
    DataFetcherFactory,
    create_fetcher,
    get_fetcher,
    list_sources,
)
from trading_system.data.storage import (
    CacheManager,
    InMemoryCache,
    RateLimiter,
    MultiSourceRateLimiter,
)
from trading_system.data.validators import (
    DataValidator,
    DataQualityReport,
)

__all__ = [
    # Fetchers
    "BaseDataFetcher",
    "DataFetcher",
    "FetchResult",
    "YahooDataFetcher",
    "AlpacaDataFetcher",
    "GoogleFinanceFetcher",
    "MockDataFetcher",
    "DataFetcherFactory",
    "create_fetcher",
    "get_fetcher",
    "list_sources",
    # Storage
    "CacheManager",
    "InMemoryCache",
    "RateLimiter",
    "MultiSourceRateLimiter",
    # Validators
    "DataValidator",
    "DataQualityReport",
]
