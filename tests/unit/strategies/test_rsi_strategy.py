"""
Unit tests for RSI strategy.
"""

import pytest
import pandas as pd
import numpy as np

from trading_system.strategies.momentum import RSIStrategy, RSIStrategyConfig


class TestRSIStrategy:
    """Tests for RSIStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create RSI strategy instance."""
        return RSIStrategy()

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        base = 100
        prices = [base]
        for _ in range(99):
            prices.append(prices[-1] + np.random.randn() * 2)

        return pd.DataFrame({
            "open": prices,
            "high": [p + abs(np.random.rand() * 2) for p in prices],
            "low": [p - abs(np.random.rand() * 2) for p in prices],
            "close": prices,
            "volume": np.random.randint(1000000, 5000000, 100)
        }, index=dates)

    def test_init_default_config(self, strategy):
        """Test initialization with default config."""
        assert strategy.period == 14
        assert strategy.overbought == 70.0
        assert strategy.oversold == 30.0

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = RSIStrategyConfig(period=20, overbought=80, oversold=20)
        strategy = RSIStrategy(config)

        assert strategy.period == 20
        assert strategy.overbought == 80
        assert strategy.oversold == 20

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert strategy.required_columns == ["close"]

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

    def test_get_indicator(self, strategy, sample_data):
        """Test getting computed indicator."""
        strategy.generate_signals(sample_data)

        rsi = strategy.get_indicator("rsi")

        assert rsi is not None
        assert len(rsi) == len(sample_data)
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError):
            RSIStrategyConfig(period=0)

        with pytest.raises(ValueError):
            RSIStrategyConfig(overbought=30, oversold=70)

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "RSIStrategy" in repr_str
        assert "period" in repr_str
