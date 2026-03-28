"""
Google Finance data fetcher.

Fetches historical stock data using yfinance library
(since the original Google Finance API was deprecated).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from trading_system.data.fetchers.base import BaseDataFetcher


class GoogleFinanceFetcher(BaseDataFetcher):
    """
    Data fetcher using yfinance library (Google Finance data source).

    Uses yfinance as a wrapper to access market data, providing the same
    interface as other fetchers in the system.

    Args:
        cache: Optional cache instance
        rate_limiter: Optional rate limiter
        timeout: Request timeout in seconds

    Example:
        >>> fetcher = GoogleFinanceFetcher()
        >>> data = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31")
        >>> print(data.head())
    """

    def __init__(
        self,
        cache: Optional[Any] = None,
        rate_limiter: Optional[Any] = None,
        timeout: int = 30
    ):
        super().__init__(cache=cache, rate_limiter=rate_limiter, timeout=timeout)
        self._yfinance = None

    @property
    def source_name(self) -> str:
        return "google"

    @property
    def _yf(self):
        """Lazy-load yfinance to avoid import at module level."""
        if self._yfinance is None:
            import yfinance
            self._yfinance = yfinance
        return self._yfinance

    def _fetch_from_api(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str
    ) -> pd.DataFrame:
        """
        Fetch data from yfinance (Google Finance data).

        Args:
            symbol: Stock symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Data interval

        Returns:
            DataFrame with OHLCV data
        """
        yf_interval = self._normalize_interval(interval)

        ticker = self._yf.Ticker(symbol.upper())
        
        df = ticker.history(
            start=start,
            end=end,
            interval=yf_interval,
            auto_adjust=True,
            back_adjust=False
        )

        if df.empty:
            raise ValueError(f"No data returned for {symbol}")

        df = df.reset_index()
        
        if "Date" in df.columns:
            df = df.rename(columns={"Date": "date"})
        elif "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "date"})
        
        df["date"] = pd.to_datetime(df["date"])
        
        if "Dividends" in df.columns:
            df = df.drop(columns=["Dividends"], errors="ignore")
        if "Stock Splits" in df.columns:
            df = df.drop(columns=["Stock Splits"], errors="ignore")

        column_mapping = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }
        df = df.rename(columns=column_mapping)
        
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = df.set_index("date")

        return df

    def _normalize_interval(self, interval: str) -> str:
        """Normalize interval to yfinance format."""
        interval_map = {
            "1m": "1m",
            "2m": "2m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "60m": "60m",
            "90m": "90m",
            "1h": "60m",
            "1d": "1d",
            "5d": "5d",
            "1wk": "1wk",
            "1mo": "1mo",
            "3mo": "3mo"
        }
        return interval_map.get(interval, "1d")

    def get_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get fundamental information for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with company info
        """
        try:
            ticker = self._yf.Ticker(symbol.upper())
            info = ticker.info
            return info if info else {}
        except Exception:
            return {}

    def get_financials(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        Get financial statements for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with 'income_stmt', 'balance_sheet', 'cash_flow' DataFrames
        """
        try:
            ticker = self._yf.Ticker(symbol.upper())
            return {
                "income_stmt": ticker.income_stmt,
                "balance_sheet": ticker.balance_sheet,
                "cash_flow": ticker.cashflow
            }
        except Exception:
            return {
                "income_stmt": pd.DataFrame(),
                "balance_sheet": pd.DataFrame(),
                "cash_flow": pd.DataFrame()
            }

    def get_actions(self, symbol: str) -> pd.DataFrame:
        """
        Get dividends and stock splits for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with dividends and splits
        """
        try:
            ticker = self._yf.Ticker(symbol.upper())
            actions = ticker.actions
            return actions if actions is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()
