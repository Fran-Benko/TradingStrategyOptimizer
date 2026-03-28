"""
Mock data fetcher for testing.

Generates synthetic OHLCV data for testing and development.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from trading_system.data.fetchers.base import BaseDataFetcher


class MockDataFetcher(BaseDataFetcher):
    """
    Mock data fetcher that generates synthetic OHLCV data.

    Useful for testing strategies without API calls.

    Args:
        seed: Random seed for reproducible data
        base_price: Base price for generated data
        volatility: Price volatility (0-1)
        cache: Optional cache instance
        rate_limiter: Optional rate limiter
        timeout: Request timeout in seconds

    Example:
        >>> fetcher = MockDataFetcher(seed=42)
        >>> data = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31")
        >>> print(data.head())
    """

    def __init__(
        self,
        seed: int = 42,
        base_price: float = 100.0,
        volatility: float = 0.02,
        cache: Optional[Any] = None,
        rate_limiter: Optional[Any] = None,
        timeout: int = 30
    ):
        super().__init__(cache=cache, rate_limiter=rate_limiter, timeout=timeout)
        self.seed = seed
        self.base_price = base_price
        self.volatility = volatility
        self._random = random.Random(seed)

    @property
    def source_name(self) -> str:
        return "mock"

    def _fetch_from_api(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str
    ) -> pd.DataFrame:
        """
        Generate mock OHLCV data.

        Args:
            symbol: Stock symbol (affects base price if known)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Data interval

        Returns:
            DataFrame with OHLCV data
        """
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")

        base_price = self._get_symbol_base_price(symbol)

        freq = self._get_frequency(interval)
        dates = pd.date_range(start=start_date, end=end_date, freq=freq)

        if len(dates) == 0:
            raise ValueError(f"No data generated for {symbol}")

        prices = [base_price]
        for _ in range(len(dates) - 1):
            change = self._random.gauss(0, self.volatility)
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.01))

        data = []
        for i, date in enumerate(dates):
            open_price = prices[i]
            close_price = prices[i]

            high_factor = abs(self._random.gauss(0, self.volatility / 2)) + 0.005
            low_factor = abs(self._random.gauss(0, self.volatility / 2)) + 0.005

            high_price = open_price * (1 + high_factor)
            low_price = open_price * (1 - low_factor)

            if close_price > high_price:
                high_price = close_price * 1.001
            if close_price < low_price:
                low_price = close_price * 0.999

            base_volume = 1000000
            volume = int(base_volume * (1 + self._random.gauss(0, 0.3)))

            data.append({
                "date": date,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": max(volume, 0)
            })

        df = pd.DataFrame(data)
        return df.set_index("date")

    def _get_symbol_base_price(self, symbol: str) -> float:
        """Get base price for a symbol (deterministic)."""
        symbol_prices = {
            "AAPL": 175.0,
            "GOOGL": 140.0,
            "MSFT": 380.0,
            "AMZN": 170.0,
            "TSLA": 250.0,
            "META": 500.0,
            "NVDA": 800.0,
            "SPY": 470.0,
            "QQQ": 400.0,
            "IWM": 200.0
        }
        return symbol_prices.get(symbol.upper(), self.base_price)

    def _get_frequency(self, interval: str) -> str:
        """Map interval to pandas frequency."""
        frequency_map = {
            "1m": "1T",
            "5m": "5T",
            "15m": "15T",
            "30m": "30T",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
            "5d": "5D",
            "1wk": "1W"
        }
        return frequency_map.get(interval, "1D")

    def generate_trade_signal(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Generate mock data with trade signals.

        Args:
            symbol: Stock symbol
            start: Start date
            end: End date
            interval: Data interval

        Returns:
            DataFrame with OHLCV and signal column
        """
        df = self.fetch(symbol, start, end, interval)
        df["signal"] = self._generate_signals(df)
        return df

    def _generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate random trade signals."""
        signals = []
        for _ in range(len(data)):
            r = self._random.random()
            if r < 0.1:
                signals.append(-1)
            elif r < 0.2:
                signals.append(1)
            else:
                signals.append(0)
        return pd.Series(signals, index=data.index)
