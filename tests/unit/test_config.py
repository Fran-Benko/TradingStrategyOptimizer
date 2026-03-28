"""
Tests for configuration module.
"""

import pytest
from trading_system.config import (
    Config,
    DataSourceConfig,
    StrategyConfig,
    BacktestConfig,
    get_config,
    validate_config,
)


class TestConfig:
    """Test Config class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.debug is False
        assert config.log_level == "INFO"
        assert config.data_dir == "data"
        assert config.cache_dir == ".cache"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = Config(
            debug=True,
            log_level="DEBUG",
            data_dir="/custom/data",
            cache_dir="/custom/cache"
        )
        
        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.data_dir == "/custom/data"
        assert config.cache_dir == "/custom/cache"

    def test_to_dict(self):
        """Test config to dict conversion."""
        config = Config()
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert "debug" in config_dict
        assert "log_level" in config_dict


class TestDataSourceConfig:
    """Test DataSourceConfig class."""

    def test_default_data_source(self):
        """Test default data source configuration."""
        config = DataSourceConfig()
        
        assert config.default_source == "yahoo"
        assert config.cache_enabled is True
        assert config.cache_ttl == 3600
        assert config.rate_limit == 5

    def test_custom_data_source(self):
        """Test custom data source configuration."""
        config = DataSourceConfig(
            default_source="alpaca",
            cache_enabled=False,
            cache_ttl=7200,
            rate_limit=10
        )
        
        assert config.default_source == "alpaca"
        assert config.cache_enabled is False
        assert config.cache_ttl == 7200
        assert config.rate_limit == 10

    def test_api_credentials(self):
        """Test API credentials configuration."""
        config = DataSourceConfig(
            alpaca_api_key="test_key",
            alpaca_secret_key="test_secret"
        )
        
        assert config.alpaca_api_key == "test_key"
        assert config.alpaca_secret_key == "test_secret"


class TestStrategyConfig:
    """Test StrategyConfig class."""

    def test_default_strategy(self):
        """Test default strategy configuration."""
        config = StrategyConfig()
        
        assert config.default_position_size == 1.0
        assert config.max_position_size == 1.0
        assert config.stop_loss is None
        assert config.take_profit is None

    def test_custom_strategy(self):
        """Test custom strategy configuration."""
        config = StrategyConfig(
            default_position_size=0.5,
            max_position_size=0.8,
            stop_loss=0.05,
            take_profit=0.15
        )
        
        assert config.default_position_size == 0.5
        assert config.max_position_size == 0.8
        assert config.stop_loss == 0.05
        assert config.take_profit == 0.15


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
            commission=0.002,
            slippage=0.001
        )
        
        assert config.initial_capital == 50000.0
        assert config.commission == 0.002
        assert config.slippage == 0.001


class TestGetConfig:
    """Test get_config function."""

    def test_get_config_default(self):
        """Test getting default config."""
        config = get_config()
        
        assert isinstance(config, Config)

    def test_get_config_custom(self):
        """Test getting custom config."""
        config = get_config(debug=True, log_level="DEBUG")
        
        assert config.debug is True
        assert config.log_level == "DEBUG"


class TestValidateConfig:
    """Test validate_config function."""

    def test_valid_config(self):
        """Test validation of valid config."""
        config = Config()
        errors = validate_config(config)
        
        assert len(errors) == 0

    def test_invalid_data_source(self):
        """Test validation catches invalid data source."""
        config = Config()
        config.data_dir = ""  # Invalid empty string
        
        errors = validate_config(config)
        
        assert len(errors) > 0

    def test_invalid_backtest_capital(self):
        """Test validation catches invalid capital."""
        config = BacktestConfig(initial_capital=-1000)
        
        errors = validate_config(config)
        
        assert len(errors) > 0
