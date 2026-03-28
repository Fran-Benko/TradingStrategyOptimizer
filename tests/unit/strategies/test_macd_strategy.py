"""
Unit tests for MACD strategy.
"""

import pytest
import pandas as pd
import numpy as np

from trading_system.strategies.momentum.macd_strategy import (
    MACDStrategy,
    MACDStrategyConfig,
    MACDHistogramStrategy,
)


class TestMACDStrategyConfig:
    """Tests for MACDStrategyConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MACDStrategyConfig()
        
        assert config.fast_period == 12
        assert config.slow_period == 26
        assert config.signal_period == 9
        assert config.histogram_threshold == 0.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = MACDStrategyConfig(
            fast_period=8,
            slow_period=20,
            signal_period=5,
            histogram_threshold=0.01
        )
        
        assert config.fast_period == 8
        assert config.slow_period == 20
        assert config.signal_period == 5
        assert config.histogram_threshold == 0.01

    def test_config_validation_fast_greater_than_slow(self):
        """Test validation fails when fast period >= slow period."""
        with pytest.raises(ValueError, match="Fast period must be less than slow"):
            MACDStrategyConfig(fast_period=30, slow_period=20)

    def test_config_validation_fast_less_than_one(self):
        """Test validation fails when fast period < 1."""
        with pytest.raises(ValueError, match="Fast period must be less than slow"):
            MACDStrategyConfig(fast_period=0, slow_period=26)

    def test_config_validation_signal_period_invalid(self):
        """Test validation fails for invalid signal period."""
        with pytest.raises(ValueError, match="Signal period must be valid"):
            MACDStrategyConfig(fast_period=12, slow_period=26, signal_period=0)


class TestMACDStrategy:
    """Tests for MACDStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create MACD strategy instance."""
        return MACDStrategy()

    @pytest.fixture
    def custom_strategy(self):
        """Create MACD strategy with custom config."""
        config = MACDStrategyConfig(
            fast_period=8,
            slow_period=20,
            signal_period=5
        )
        return MACDStrategy(config)

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        prices = 100 + np.cumsum(np.random.randn(100) * 2)

        return pd.DataFrame({
            "open": prices + np.random.randn(100) * 0.5,
            "high": prices + abs(np.random.randn(100)) * 2,
            "low": prices - abs(np.random.randn(100)) * 2,
            "close": prices,
            "volume": np.random.randint(1000000, 5000000, 100)
        }, index=dates)

    def test_init_default_config(self, strategy):
        """Test initialization with default config."""
        assert strategy.fast_period == 12
        assert strategy.slow_period == 26
        assert strategy.signal_period == 9
        assert strategy.histogram_threshold == 0.0

    def test_init_custom_config(self, custom_strategy):
        """Test initialization with custom config."""
        assert custom_strategy.fast_period == 8
        assert custom_strategy.slow_period == 20
        assert custom_strategy.signal_period == 5

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert strategy.required_columns == ["close"]

    def test_min_periods(self, strategy):
        """Test minimum periods calculation."""
        # min_periods = slow_period + signal_period = 26 + 9 = 35
        assert strategy.min_periods == 35

    def test_min_periods_custom(self, custom_strategy):
        """Test min periods with custom config."""
        # min_periods = slow_period + signal_period = 20 + 5 = 25
        assert custom_strategy.min_periods == 25

    def test_generate_signals_returns_array(self, strategy, sample_data):
        """Test that generate_signals returns numpy array."""
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)

    def test_generate_signals_values(self, strategy, sample_data):
        """Test that signals are valid (-1, 0, 1)."""
        signals = strategy.generate_signals(sample_data)

        assert set(signals).issubset({-1, 0, 1})

    def test_generate_signals_with_insufficient_data(self, strategy):
        """Test with insufficient data raises error."""
        small_data = pd.DataFrame({
            "close": [100, 101, 102]
        })

        with pytest.raises(ValueError, match="Insufficient data"):
            strategy.generate_signals(small_data)

    def test_generate_signals_with_missing_columns(self, strategy):
        """Test with missing columns raises error."""
        incomplete_data = pd.DataFrame({"open": [100, 101, 102]})

        with pytest.raises(ValueError, match="Missing required columns"):
            strategy.generate_signals(incomplete_data)

    def test_get_indicator_macd(self, strategy, sample_data):
        """Test getting MACD indicator."""
        strategy.generate_signals(sample_data)

        macd = strategy.get_indicator("macd")

        assert macd is not None
        assert len(macd) == len(sample_data)

    def test_get_indicator_signal(self, strategy, sample_data):
        """Test getting signal line indicator."""
        strategy.generate_signals(sample_data)

        signal = strategy.get_indicator("signal")

        assert signal is not None
        assert len(signal) == len(sample_data)

    def test_get_indicator_histogram(self, strategy, sample_data):
        """Test getting histogram indicator."""
        strategy.generate_signals(sample_data)

        histogram = strategy.get_indicator("histogram")

        assert histogram is not None
        assert len(histogram) == len(sample_data)

    def test_get_indicator_nonexistent(self, strategy, sample_data):
        """Test getting nonexistent indicator returns None."""
        strategy.generate_signals(sample_data)

        indicator = strategy.get_indicator("nonexistent")

        assert indicator is None

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "MACDStrategy" in repr_str
        assert "fast_period" in repr_str


class TestMACDHistogramStrategy:
    """Tests for MACDHistogramStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create MACD histogram strategy instance."""
        return MACDHistogramStrategy()

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        prices = 100 + np.cumsum(np.random.randn(100) * 2)

        return pd.DataFrame({
            "open": prices + np.random.randn(100) * 0.5,
            "high": prices + abs(np.random.randn(100)) * 2,
            "low": prices - abs(np.random.randn(100)) * 2,
            "close": prices,
            "volume": np.random.randint(1000000, 5000000, 100)
        }, index=dates)

    def test_init(self, strategy):
        """Test initialization."""
        assert strategy.fast_period == 12
        assert strategy.slow_period == 26
        assert strategy.signal_period == 9

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert strategy.required_columns == ["close"]

    def test_min_periods(self, strategy):
        """Test minimum periods calculation."""
        assert strategy.min_periods == 35

    def test_generate_signals_returns_array(self, strategy, sample_data):
        """Test that generate_signals returns numpy array."""
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)

    def test_generate_signals_values(self, strategy, sample_data):
        """Test that signals are valid (-1, 0, 1)."""
        signals = strategy.generate_signals(sample_data)

        assert set(signals).issubset({-1, 0, 1})

    def test_generate_signals_with_insufficient_data(self, strategy):
        """Test with insufficient data raises error."""
        small_data = pd.DataFrame({
            "close": [100, 101, 102]
        })

        with pytest.raises(ValueError, match="Insufficient data"):
            strategy.generate_signals(small_data)

    def test_get_indicator_histogram(self, strategy, sample_data):
        """Test getting histogram indicator."""
        strategy.generate_signals(sample_data)

        histogram = strategy.get_indicator("histogram")

        assert histogram is not None
        assert len(histogram) == len(sample_data)

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "MACDHistogramStrategy" in repr_str
