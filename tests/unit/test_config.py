"""
Tests for configuration module.
"""

import pytest
from trading_system.config import (
    AlpacaConfig,
    GoogleFinanceConfig,
    DataConfig,
    BacktestConfig,
    LoggingConfig,
    TradingSystemConfig,
)


class TestAlpacaConfig:
    """Test AlpacaConfig class."""

    def test_default_config(self):
        """Test default Alpaca configuration."""
        config = AlpacaConfig(
            api_key="test_key",
            secret_key="test_secret"
        )
        
        assert config.api_key == "test_key"
        assert config.secret_key == "test_secret"
        assert config.base_url == "https://paper-api.alpaca.markets"

    def test_custom_url(self):
        """Test custom base URL."""
        config = AlpacaConfig(
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://live-api.alpaca.markets"
        )
        
        assert config.base_url == "https://live-api.alpaca.markets"


class TestGoogleFinanceConfig:
    """Test GoogleFinanceConfig class."""

    def test_default_config(self):
        """Test default Google Finance configuration."""
        config = GoogleFinanceConfig()
        
        assert config.enabled is True


class TestDataConfig:
    """Test DataConfig class."""

    def test_default_data_config(self):
        """Test default data configuration."""
        config = DataConfig()
        
        assert config.default_source == "yahoo"
        assert config.cache_enabled is True

    def test_custom_data_config(self):
        """Test custom data configuration."""
        config = DataConfig(
            default_source="alpaca",
            cache_enabled=False
        )
        
        assert config.default_source == "alpaca"
        assert config.cache_enabled is False


class TestBacktestConfig:
    """Test BacktestConfig class."""

    def test_default_backtest(self):
        """Test default backtest configuration."""
        config = BacktestConfig()
        
        assert config.initial_capital == 100000.0
        assert config.commission == 0.001
        assert config.slippage == 0.0005

    def test_custom_backtest(self):
        """Test custom backtest configuration."""
        config = BacktestConfig(
            initial_capital=50000.0,
            commission=0.002
        )
        
        assert config.initial_capital == 50000.0
        assert config.commission == 0.002


class TestLoggingConfig:
    """Test LoggingConfig class."""

    def test_default_logging(self):
        """Test default logging configuration."""
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert config.format == "json"


class TestTradingSystemConfig:
    """Test TradingSystemConfig class."""

    def test_default_system_config(self):
        """Test default system configuration."""
        config = TradingSystemConfig()
        
        assert config.name == "trading-system"
        assert config.debug is False

    def test_custom_system_config(self):
        """Test custom system configuration."""
        config = TradingSystemConfig(
            name="my-trading-bot",
            debug=True
        )
        
        assert config.name == "my-trading-bot"
        assert config.debug is True
