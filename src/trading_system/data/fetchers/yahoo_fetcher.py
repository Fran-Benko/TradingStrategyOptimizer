"""
Yahoo Finance data fetcher.

Fetches historical stock data from Yahoo Finance API.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
import requests

from trading_system.data.fetchers.base import BaseDataFetcher


class YahooDataFetcher(BaseDataFetcher):
    """
    Data fetcher for Yahoo Finance API.

    Args:
        cache: Optional cache instance
        rate_limiter: Optional rate limiter
        timeout: Request timeout in seconds

    Example:
        >>> fetcher = YahooDataFetcher()
        >>> data = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31")
        >>> print(data.head())
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    def __init__(
        self,
        cache: Optional[Any] = None,
        rate_limiter: Optional[Any] = None,
        timeout: int = 30
    ):
        super().__init__(cache=cache, rate_limiter=rate_limiter, timeout=timeout)

    @property
    def source_name(self) -> str:
        return "yahoo"

    def _setup_session(self, session: requests.Session) -> None:
        """Setup session with headers."""
        session.headers.update(self.HEADERS)

    def _fetch_from_api(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str
    ) -> pd.DataFrame:
        """
        Fetch data from Yahoo Finance API.

        Args:
            symbol: Stock symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Data interval

        Returns:
            DataFrame with OHLCV data
        """
        start_ts = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp())

        params = {
            "period1": start_ts,
            "period2": end_ts,
            "interval": self._normalize_interval(interval),
            "events": "history"
        }

        url = f"{self.BASE_URL}/{symbol.upper()}"
        session = self._get_session()

        response = session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        if "chart" not in data or "result" not in data["chart"]:
            raise ValueError(f"Invalid response for {symbol}")

        result = data["chart"]["result"]
        if not result:
            raise ValueError(f"No data returned for {symbol}")

        result = result[0]

        if "timestamp" not in result or "indicators" not in result:
            raise ValueError(f"Incomplete data for {symbol}")

        timestamps = result["timestamp"]
        indicators = result["indicators"]

        quote = indicators.get("quote", [{}])[0]
        volumes_list = indicators.get("volume", [{}])
        volumes_data = volumes_list[0] if volumes_list else {}

        df = pd.DataFrame({
            "date": pd.to_datetime(timestamps, unit="s"),
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": volumes_data.get("volume") if volumes_data else None
        })

        df = df.dropna(subset=["close"])

        return df.set_index("date")

    def _normalize_interval(self, interval: str) -> str:
        """Normalize interval to Yahoo format."""
        interval_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "4h",
            "1d": "1d", "5d": "5d", "1wk": "1wk", "1mo": "1mo"
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
        import requests

        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol.upper()}"
        params = {"modules": "summaryDetail,defaultKeyStatistics,financialData"}

        try:
            response = requests.get(
                url,
                params=params,
                headers=self.HEADERS,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get("quoteSummary", {}).get("result", [{}])[0]
        except Exception:
            return {}
