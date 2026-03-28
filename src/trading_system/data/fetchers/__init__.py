"""
Data fetchers module.

Provides data fetching from various sources.
"""

from trading_system.data.fetchers.base import BaseDataFetcher, DataFetcher, FetchResult
from trading_system.data.fetchers.yahoo_fetcher import YahooDataFetcher
from trading_system.data.fetchers.alpaca_fetcher import AlpacaDataFetcher
from trading_system.data.fetchers.google_finance import GoogleFinanceFetcher
from trading_system.data.fetchers.mock_fetcher import MockDataFetcher
from trading_system.data.fetchers.factory import (
    DataFetcherFactory,
    create_fetcher,
    get_fetcher,
    list_sources,
)

__all__ = [
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
]
