"""
Alpaca data fetcher.

Fetches historical stock data from Alpaca Markets API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from trading_system.data.fetchers.base import BaseDataFetcher


class AlpacaDataFetcher(BaseDataFetcher):
    """
    Data fetcher for Alpaca Markets API.

    Requires ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables.

    Args:
        api_key: Alpaca API key (defaults to env var)
        secret_key: Alpaca secret key (defaults to env var)
        base_url: Alpaca base URL (paper or live)
        cache: Optional cache instance
        rate_limiter: Optional rate limiter
        timeout: Request timeout in seconds

    Example:
        >>> fetcher = AlpacaDataFetcher()
        >>> data = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31")
        >>> print(data.head())
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: str = "https://data.alpaca.markets",
        cache: Optional[Any] = None,
        rate_limiter: Optional[Any] = None,
        timeout: int = 30
    ):
        import os
        super().__init__(cache=cache, rate_limiter=rate_limiter, timeout=timeout)

        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")
        self.base_url = base_url.rstrip("/")

        if not self.api_key or not self.secret_key:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Alpaca API keys not configured")

    @property
    def source_name(self) -> str:
        return "alpaca"

    def _setup_session(self, session: requests.Session) -> None:
        """Setup session with Alpaca authentication."""
        session.headers.update({
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key
        })

    def _fetch_from_api(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str
    ) -> pd.DataFrame:
        """
        Fetch data from Alpaca API.

        Args:
            symbol: Stock symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Data interval

        Returns:
            DataFrame with OHLCV data
        """
        timeframe = self._normalize_timeframe(interval)

        url = f"{self.base_url}/v2/stocks/{symbol.upper()}/bars"
        params = {
            "start": start,
            "end": end,
            "timeframe": timeframe,
            "limit": 10000,
            "adjustment": "split"
        }

        session = self._get_session()
        all_bars = []
        page_token = None

        while True:
            if page_token:
                params["page_token"] = page_token

            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            if "bars" not in data or not data["bars"]:
                break

            all_bars.extend(data["bars"])

            page_token = data.get("next_page_token")
            if not page_token:
                break

        if not all_bars:
            raise ValueError(f"No data returned for {symbol}")

        df = pd.DataFrame(all_bars)

        df = df.rename(columns={
            "t": "date",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume"
        })

        df["date"] = pd.to_datetime(df["date"])
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = df.set_index("date")

        return df

    def _normalize_timeframe(self, interval: str) -> str:
        """Normalize interval to Alpaca timeframe format."""
        timeframe_map = {
            "1m": "1Min",
            "5m": "5Min",
            "15m": "15Min",
            "30m": "30Min",
            "1h": "1Hour",
            "4h": "4Hour",
            "1d": "1Day",
            "1wk": "1Week"
        }
        return timeframe_map.get(interval, "1Day")

    def get_bars_batch(
        self,
        symbols: List[str],
        start: str,
        end: str,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Get bars for multiple symbols in a single API call.

        Args:
            symbols: List of stock symbols
            start: Start date
            end: End date
            interval: Data interval

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        timeframe = self._normalize_timeframe(interval)

        url = f"{self.base_url}/v2/stocks/bars"
        params = {
            "symbols": ",".join(s.upper() for s in symbols),
            "start": start,
            "end": end,
            "timeframe": timeframe,
            "limit": 10000,
            "adjustment": "split"
        }

        session = self._get_session()
        response = session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results = {}

        for symbol, bars in data.get("bars", {}).items():
            if bars:
                df = pd.DataFrame(bars)
                df = df.rename(columns={
                    "t": "date",
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume"
                })
                df["date"] = pd.to_datetime(df["date"])
                df = df[["date", "open", "high", "low", "close", "volume"]]
                results[symbol] = df.set_index("date")
            else:
                results[symbol] = pd.DataFrame()

        return results

    def get_trades(
        self,
        symbol: str,
        start: str,
        end: str,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Get trade data for a symbol.

        Args:
            symbol: Stock symbol
            start: Start date
            end: End date
            limit: Maximum number of trades

        Returns:
            DataFrame with trade data
        """
        url = f"{self.base_url}/v2/stocks/{symbol.upper()}/trades"
        params = {
            "start": start,
            "end": end,
            "limit": limit
        }

        session = self._get_session()
        response = session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        if "trades" not in data or not data["trades"]:
            return pd.DataFrame()

        df = pd.DataFrame(data["trades"])
        df = df.rename(columns={
            "t": "date",
            "p": "price",
            "s": "size",
            "c": "conditions"
        })
        df["date"] = pd.to_datetime(df["date"])

        return df
