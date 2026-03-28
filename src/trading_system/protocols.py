"""
Core protocols and type definitions for the trading system.

This module defines the interfaces that all components must implement,
ensuring consistency and type safety across the system.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

import pandas as pd


class DataFetcher(Protocol):
    """Protocol for data fetching implementations."""

    @abstractmethod
    async def fetch_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical market data.

        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval (1m, 5m, 1h, 1d, etc.)

        Returns:
            DataFrame with OHLCV data

        Raises:
            DataFetchError: If data cannot be fetched
        """
        ...

    @abstractmethod
    async def fetch_realtime(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch real-time market data.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with current market data

        Raises:
            DataFetchError: If data cannot be fetched
        """
        ...

    @abstractmethod
    def get_rate_limit(self) -> Dict[str, int]:
        """
        Get rate limit information.

        Returns:
            Dictionary with rate limit details
        """
        ...


class DataValidator(Protocol):
    """Protocol for data validation implementations."""

    @abstractmethod
    def validate(self, data: pd.DataFrame) -> bool:
        """
        Validate market data.

        Args:
            data: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        ...

    @abstractmethod
    def get_errors(self) -> List[str]:
        """
        Get validation errors.

        Returns:
            List of error messages
        """
        ...


class Strategy(Protocol):
    """Protocol for trading strategy implementations."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize strategy parameters and state."""
        ...

    @abstractmethod
    def next(self) -> None:
        """
        Execute strategy logic for the current bar.
        Called by backtesting engine for each data point.
        """
        ...

    @abstractmethod
    def get_signals(self) -> Dict[str, Any]:
        """
        Get current trading signals.

        Returns:
            Dictionary with signal information
        """
        ...

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get strategy parameters.

        Returns:
            Dictionary with parameter values
        """
        ...


class MetricsCalculator(Protocol):
    """Protocol for metrics calculation implementations."""

    @abstractmethod
    def calculate_returns(self, trades: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate return metrics.

        Args:
            trades: DataFrame with trade data

        Returns:
            Dictionary with return metrics
        """
        ...

    @abstractmethod
    def calculate_risk(self, trades: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate risk metrics.

        Args:
            trades: DataFrame with trade data

        Returns:
            Dictionary with risk metrics
        """
        ...

    @abstractmethod
    def calculate_ratios(self, trades: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate risk-adjusted ratios.

        Args:
            trades: DataFrame with trade data

        Returns:
            Dictionary with ratio metrics
        """
        ...


class BacktestEngine(Protocol):
    """Protocol for backtesting engine implementations."""

    @abstractmethod
    def run(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        initial_capital: float = 100000.0,
    ) -> Dict[str, Any]:
        """
        Run backtest with given strategy and data.

        Args:
            strategy: Strategy to test
            data: Historical market data
            initial_capital: Starting capital

        Returns:
            Dictionary with backtest results
        """
        ...

    @abstractmethod
    def get_trades(self) -> pd.DataFrame:
        """
        Get executed trades from backtest.

        Returns:
            DataFrame with trade details
        """
        ...

    @abstractmethod
    def get_equity_curve(self) -> pd.DataFrame:
        """
        Get equity curve from backtest.

        Returns:
            DataFrame with equity values over time
        """
        ...


class Optimizer(Protocol):
    """Protocol for strategy optimization implementations."""

    @abstractmethod
    def optimize(
        self,
        strategy_class: type,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        metric: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        """
        Optimize strategy parameters.

        Args:
            strategy_class: Strategy class to optimize
            data: Historical data for optimization
            param_grid: Parameter grid to search
            metric: Optimization metric

        Returns:
            Dictionary with optimal parameters and results
        """
        ...

    @abstractmethod
    def get_results(self) -> pd.DataFrame:
        """
        Get optimization results.

        Returns:
            DataFrame with all tested parameter combinations
        """
        ...

# Made with Bob
