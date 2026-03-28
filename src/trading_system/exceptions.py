"""
Custom exceptions for the trading system.

This module defines all custom exceptions used throughout the system,
providing clear error handling and debugging information.
"""

from typing import Optional, List


class TradingSystemError(Exception):
    """Base exception for all trading system errors."""

    pass


class DataFetchError(TradingSystemError):
    """Raised when data cannot be fetched from a source."""

    def __init__(
        self,
        source_or_message: str = "unknown",
        symbol: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        if symbol is None and reason is None:
            self.source = "unknown"
            self.symbol = None
            self.reason = source_or_message
            super().__init__(f"Failed to fetch data: {source_or_message}")
        else:
            self.source = source_or_message
            self.symbol = symbol
            self.reason = reason
            super().__init__(f"Failed to fetch {symbol} from {source_or_message}: {reason}")


class DataValidationError(TradingSystemError):
    """Raised when data validation fails."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Data validation failed: {', '.join(errors)}")


class RateLimitError(TradingSystemError):
    """Raised when rate limit is exceeded."""

    def __init__(self, source: str, retry_after: int) -> None:
        self.source = source
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {source}. Retry after {retry_after}s")


class StrategyError(TradingSystemError):
    """Raised when strategy execution fails."""

    def __init__(self, strategy_name: str, reason: str) -> None:
        self.strategy_name = strategy_name
        self.reason = reason
        super().__init__(f"Strategy {strategy_name} failed: {reason}")


class BacktestError(TradingSystemError):
    """Raised when backtesting fails."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Backtest failed: {reason}")


class OptimizationError(TradingSystemError):
    """Raised when optimization fails."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Optimization failed: {reason}")


class ConfigurationError(TradingSystemError):
    """Raised when configuration is invalid."""

    def __init__(self, parameter: str, reason: str) -> None:
        self.parameter = parameter
        self.reason = reason
        super().__init__(f"Invalid configuration for {parameter}: {reason}")


class InsufficientDataError(TradingSystemError):
    """Raised when there is insufficient data for analysis."""

    def __init__(self, required: int, available: int) -> None:
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient data: required {required} points, got {available}"
        )

# Made with Bob
