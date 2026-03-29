"""
Tests for exceptions module.
"""

import pytest
from trading_system.exceptions import (
    TradingSystemError,
    DataFetchError,
    DataValidationError,
    RateLimitError,
    StrategyError,
    BacktestError,
    OptimizationError,
    ConfigurationError,
    InsufficientDataError,
)


class TestTradingSystemError:
    """Test base TradingSystemError."""

    def test_base_error(self):
        """Test base error can be raised."""
        with pytest.raises(TradingSystemError):
            raise TradingSystemError("Base error message")

    def test_error_str(self):
        """Test error string representation."""
        error = TradingSystemError("Test error")
        assert str(error) == "Test error"


class TestDataFetchError:
    """Test DataFetchError."""

    def test_data_fetch_error(self):
        """Test DataFetchError can be raised."""
        with pytest.raises(DataFetchError):
            raise DataFetchError("Failed to fetch data")

    def test_data_fetch_error_inheritance(self):
        """Test DataFetchError inherits from TradingSystemError."""
        error = DataFetchError("Test")
        assert isinstance(error, TradingSystemError)


class TestDataValidationError:
    """Test DataValidationError."""

    def test_data_validation_error(self):
        """Test DataValidationError can be raised."""
        with pytest.raises(DataValidationError):
            raise DataValidationError(["error1", "error2"])

    def test_data_validation_error_inheritance(self):
        """Test DataValidationError inherits from TradingSystemError."""
        error = DataValidationError(["test"])
        assert isinstance(error, TradingSystemError)


class TestRateLimitError:
    """Test RateLimitError."""

    def test_rate_limit_error(self):
        """Test RateLimitError can be raised."""
        with pytest.raises(RateLimitError):
            raise RateLimitError("alpaca", 60)

    def test_rate_limit_error_inheritance(self):
        """Test RateLimitError inherits from TradingSystemError."""
        error = RateLimitError("alpaca", 60)
        assert isinstance(error, TradingSystemError)
        assert error.source == "alpaca"
        assert error.retry_after == 60


class TestStrategyError:
    """Test StrategyError."""

    def test_strategy_error(self):
        """Test StrategyError can be raised."""
        with pytest.raises(StrategyError):
            raise StrategyError("RSI", "Invalid parameters")

    def test_strategy_error_inheritance(self):
        """Test StrategyError inherits from TradingSystemError."""
        error = StrategyError("RSI", "Invalid parameters")
        assert isinstance(error, TradingSystemError)
        assert error.strategy_name == "RSI"
        assert error.reason == "Invalid parameters"


class TestBacktestError:
    """Test BacktestError."""

    def test_backtest_error(self):
        """Test BacktestError can be raised."""
        with pytest.raises(BacktestError):
            raise BacktestError("Insufficient data")

    def test_backtest_error_inheritance(self):
        """Test BacktestError inherits from TradingSystemError."""
        error = BacktestError("Test")
        assert isinstance(error, TradingSystemError)


class TestOptimizationError:
    """Test OptimizationError."""

    def test_optimization_error(self):
        """Test OptimizationError can be raised."""
        with pytest.raises(OptimizationError):
            raise OptimizationError("No convergence")

    def test_optimization_error_inheritance(self):
        """Test OptimizationError inherits from TradingSystemError."""
        error = OptimizationError("Test")
        assert isinstance(error, TradingSystemError)


class TestConfigurationError:
    """Test ConfigurationError."""

    def test_configuration_error(self):
        """Test ConfigurationError can be raised."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("api_key", "Missing required field")

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inherits from TradingSystemError."""
        error = ConfigurationError("api_key", "Missing")
        assert isinstance(error, TradingSystemError)
        assert error.parameter == "api_key"
        assert error.reason == "Missing"


class TestInsufficientDataError:
    """Test InsufficientDataError."""

    def test_insufficient_data_error(self):
        """Test InsufficientDataError can be raised."""
        with pytest.raises(InsufficientDataError):
            raise InsufficientDataError(100, 50)

    def test_insufficient_data_error_inheritance(self):
        """Test InsufficientDataError inherits from TradingSystemError."""
        error = InsufficientDataError(100, 50)
        assert isinstance(error, TradingSystemError)
        assert error.required == 100
        assert error.available == 50


class TestExceptionHierarchy:
    """Test exception hierarchy."""

    def test_hierarchy(self):
        """Test exception inheritance hierarchy."""
        assert issubclass(DataFetchError, TradingSystemError)
        assert issubclass(DataValidationError, TradingSystemError)
        assert issubclass(RateLimitError, TradingSystemError)
        assert issubclass(StrategyError, TradingSystemError)
        assert issubclass(BacktestError, TradingSystemError)
        assert issubclass(OptimizationError, TradingSystemError)
        assert issubclass(ConfigurationError, TradingSystemError)
        assert issubclass(InsufficientDataError, TradingSystemError)

    def test_all_errors_catchable(self):
        """Test that all errors can be caught by base class."""
        with pytest.raises(TradingSystemError):
            raise InsufficientDataError(100, 50)
