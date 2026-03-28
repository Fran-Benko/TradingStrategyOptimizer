"""
Configuration management for the trading system.

This module handles all configuration using Pydantic for validation
and type safety. Configuration can be loaded from environment variables
or .env files.
"""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AlpacaConfig(BaseSettings):
    """Alpaca API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ALPACA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(..., description="Alpaca API key")
    secret_key: str = Field(..., description="Alpaca secret key")
    base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        description="Alpaca API base URL",
    )
    data_url: str = Field(
        default="https://data.alpaca.markets",
        description="Alpaca data API URL",
    )


class GoogleFinanceConfig(BaseSettings):
    """Google Finance API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_FINANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: Optional[str] = Field(default=None, description="Google Finance API key")


class DataConfig(BaseSettings):
    """Data fetching configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DATA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cache_enabled: bool = Field(default=True, description="Enable data caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    rate_limit_requests: int = Field(
        default=100, description="Max requests per minute"
    )
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: int = Field(default=1, description="Delay between retries in seconds")
    timeout: int = Field(default=30, description="Request timeout in seconds")

    @field_validator("cache_ttl", "rate_limit_window", "timeout")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Validate that value is positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v


class BacktestConfig(BaseSettings):
    """Backtesting configuration."""

    model_config = SettingsConfigDict(
        env_prefix="BACKTEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    initial_capital: float = Field(
        default=100000.0, description="Initial capital for backtesting"
    )
    commission: float = Field(default=0.001, description="Commission rate (0.1%)")
    slippage: float = Field(default=0.0005, description="Slippage rate (0.05%)")
    position_size: float = Field(
        default=0.95, description="Max position size as fraction of capital"
    )

    @field_validator("initial_capital")
    @classmethod
    def validate_capital(cls, v: float) -> float:
        """Validate initial capital is positive."""
        if v <= 0:
            raise ValueError("Initial capital must be positive")
        return v

    @field_validator("commission", "slippage")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        """Validate rate is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Rate must be between 0 and 1")
        return v


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="json", description="Log format (json or console)"
    )
    file_path: Optional[str] = Field(
        default=None, description="Log file path (None for stdout)"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Level must be one of {valid_levels}")
        return v_upper


class TradingSystemConfig(BaseSettings):
    """Main trading system configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-configurations
    alpaca: AlpacaConfig = Field(default_factory=AlpacaConfig)
    google_finance: GoogleFinanceConfig = Field(default_factory=GoogleFinanceConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # General settings
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v


# Global configuration instance
_config: Optional[TradingSystemConfig] = None


def get_config() -> TradingSystemConfig:
    """
    Get the global configuration instance.

    Returns:
        TradingSystemConfig instance

    Example:
        >>> config = get_config()
        >>> print(config.backtest.initial_capital)
        100000.0
    """
    global _config
    if _config is None:
        _config = TradingSystemConfig()
    return _config


def reload_config() -> TradingSystemConfig:
    """
    Reload configuration from environment/files.

    Returns:
        New TradingSystemConfig instance

    Example:
        >>> config = reload_config()
    """
    global _config
    _config = TradingSystemConfig()
    return _config