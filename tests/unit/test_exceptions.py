"""
Tests for exceptions module.
"""

import pytest
from trading_system.exceptions import (
    TradingSystemError,
    DataError,
    DataFetchError,
    DataValidationError,
    StrategyError,
    StrategyExecutionError,
    BacktestError,
    OptimizationError,
    ConfigurationError,
    APIError,
    RateLimitError,
    AuthenticationError,
)


class TestTradingSystemError:
    """Test base TradingSystemError."""

    def test_base_error(self):
        """Test base error can be raised."""
        with pytest.raises(TradingSystemError):
            raise TradingSystemError("Base error message")

    def test_error_with_code(self):
        """Test error with code."""
        error = TradingSystemError("Test error", code="TEST_001")
        assert error.code == "TEST_001"

    def test_error_str(self):
        """Test error string representation."""
        error = TradingSystemError("Test error")
        assert str(error) == "Test error"


class TestDataError:
    """Test DataError."""

    def test_data_error(self):
        """Test DataError can be raised."""
        with pytest.raises(DataError):
            raise DataError("Data error occurred")

    def test_data_error_inheritance(self):
        """Test DataError inherits from TradingSystemError."""
        error = DataError("Test")
        assert isinstance(error, TradingSystemError)


class TestDataFetchError:
    """Test DataFetchError."""

    def test_data_fetch_error(self):
        """Test DataFetchError can be raised."""
        with pytest.raises(DataFetchError):
            raise DataFetchError("Failed to fetch data")

    def test_data_fetch_error_with_symbol(self):
        """Test DataFetchError includes symbol."""
        error = DataFetchError("Fetch failed", symbol="AAPL")
        assert error.symbol == "AAPL"

    def test_data_fetch_error_inheritance(self):
        """Test DataFetchError inherits from DataError."""
        error = DataFetchError("Test")
        assert isinstance(error, DataError)


class TestDataValidationError:
    """Test DataValidationError."""

    def test_data_validation_error(self):
        """Test DataValidationError can be raised."""
        with pytest.raises(DataValidationError):
            raise DataValidationError("Invalid data format")

    def test_data_validation_error_details(self):
        """Test DataValidationError includes details."""
        error = DataValidationError("Validation failed", field="close", value=None)
        assert error.field == "close"
        assert error.value is None

    def test_data_validation_error_inheritance(self):
        """Test DataValidationError inherits from DataError."""
        error = DataValidationError("Test")
        assert isinstance(error, DataError)


class TestStrategyError:
    """Test StrategyError."""

    def test_strategy_error(self):
        """Test StrategyError can be raised."""
        with pytest.raises(StrategyError):
            raise StrategyError("Strategy error")

    def test_strategy_error_inheritance(self):
        """Test StrategyError inherits from TradingSystemError."""
        error = StrategyError("Test")
        assert isinstance(error, TradingSystemError)


class TestStrategyExecutionError:
    """Test StrategyExecutionError."""

    def test_strategy_execution_error(self):
        """Test StrategyExecutionError can be raised."""
        with pytest.raises(StrategyExecutionError):
            raise StrategyExecutionError("Execution failed")

    def test_strategy_execution_error_inheritance(self):
        """Test StrategyExecutionError inherits from StrategyError."""
        error = StrategyExecutionError("Test")
        assert isinstance(error, StrategyError)


class TestBacktestError:
    """Test BacktestError."""

    def test_backtest_error(self):
        """Test BacktestError can be raised."""
        with pytest.raises(BacktestError):
            raise BacktestError("Backtest failed")

    def test_backtest_error_inheritance(self):
        """Test BacktestError inherits from TradingSystemError."""
        error = BacktestError("Test")
        assert isinstance(error, TradingSystemError)


class TestOptimizationError:
    """Test OptimizationError."""

    def test_optimization_error(self):
        """Test OptimizationError can be raised."""
        with pytest.raises(OptimizationError):
            raise OptimizationError("Optimization failed")

    def test_optimization_error_inheritance(self):
        """Test OptimizationError inherits from TradingSystemError."""
        error = OptimizationError("Test")
        assert isinstance(error, TradingSystemError)


class TestConfigurationError:
    """Test ConfigurationError."""

    def test_configuration_error(self):
        """Test ConfigurationError can be raised."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Invalid configuration")

    def test_configuration_error_with_field(self):
        """Test ConfigurationError includes field info."""
        error = ConfigurationError("Invalid value", field="api_key", value="")
        assert error.field == "api_key"

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inherits from TradingSystemError."""
        error = ConfigurationError("Test")
        assert isinstance(error, TradingSystemError)


class TestAPIError:
    """Test APIError."""

    def test_api_error(self):
        """Test APIError can be raised."""
        with pytest.raises(APIError):
            raise APIError("API request failed")

    def test_api_error_with_status(self):
        """Test APIError includes status code."""
        error = APIError("Request failed", status_code=404)
        assert error.status_code == 404

    def test_api_error_inheritance(self):
        """Test APIError inherits from TradingSystemError."""
        error = APIError("Test")
        assert isinstance(error, TradingSystemError)


class TestRateLimitError:
    """Test RateLimitError."""

    def test_rate_limit_error(self):
        """Test RateLimitError can be raised."""
        with pytest.raises(RateLimitError):
            raise RateLimitError("Rate limit exceeded")

    def test_rate_limit_error_retry_after(self):
        """Test RateLimitError includes retry info."""
        error = RateLimitError("Rate limit", retry_after=60)
        assert error.retry_after == 60

    def test_rate_limit_error_inheritance(self):
        """Test RateLimitError inherits from APIError."""
        error = RateLimitError("Test")
        assert isinstance(error, APIError)


class TestAuthenticationError:
    """Test AuthenticationError."""

    def test_authentication_error(self):
        """Test AuthenticationError can be raised."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Authentication failed")

    def test_authentication_error_inheritance(self):
        """Test AuthenticationError inherits from APIError."""
        error = AuthenticationError("Test")
        assert isinstance(error, APIError)


class TestExceptionHierarchy:
    """Test exception hierarchy."""

    def test_hierarchy(self):
        """Test exception inheritance hierarchy."""
        assert issubclass(DataFetchError, DataError)
        assert issubclass(DataValidationError, DataError)
        assert issubclass(DataError, TradingSystemError)
        
        assert issubclass(StrategyExecutionError, StrategyError)
        assert issubclass(StrategyError, TradingSystemError)
        
        assert issubclass(BacktestError, TradingSystemError)
        assert issubclass(OptimizationError, TradingSystemError)
        assert issubclass(ConfigurationError, TradingSystemError)
        
        assert issubclass(AuthenticationError, APIError)
        assert issubclass(RateLimitError, APIError)
        assert issubclass(APIError, TradingSystemError)

    def test_all_errors_catchable(self):
        """Test that all errors can be caught by base class."""
        with pytest.raises(TradingSystemError):
            raise AuthenticationError("Test")


class TestExceptionMessages:
    """Test exception messages."""

    def test_error_message_format(self):
        """Test error messages are properly formatted."""
        error = DataFetchError("Failed to fetch AAPL data", symbol="AAPL")
        message = str(error)
        
        assert "AAPL" in message
        assert "Failed to fetch" in message

    def test_error_context(self):
        """Test error includes context."""
        error = BacktestError(
            "Backtest failed",
            strategy="RSI",
            period="2023-01-01 to 2023-12-31"
        )
        
        assert error.args[0] == "Backtest failed"
