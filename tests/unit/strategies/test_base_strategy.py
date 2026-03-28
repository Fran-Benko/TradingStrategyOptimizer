"""
Unit tests for BaseStrategy.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

from trading_system.strategies.base import (
    BaseStrategy,
    Signal,
    SignalType,
    StrategyConfig,
)


class TestSignalType:
    """Tests for SignalType enum."""

    def test_signal_type_values(self):
        """Test SignalType enum values."""
        assert SignalType.BUY.value == 1
        assert SignalType.SELL.value == -1
        assert SignalType.HOLD.value == 0

    def test_signal_type_from_int(self):
        """Test creating SignalType from integer."""
        assert SignalType(1) == SignalType.BUY
        assert SignalType(-1) == SignalType.SELL
        assert SignalType(0) == SignalType.HOLD


class TestSignal:
    """Tests for Signal dataclass."""

    def test_signal_creation(self):
        """Test creating a Signal instance."""
        signal = Signal(
            date=pd.Timestamp("2023-01-01"),
            type=SignalType.BUY,
            price=100.0,
            quantity=1.0
        )

        assert signal.date == pd.Timestamp("2023-01-01")
        assert signal.type == SignalType.BUY
        assert signal.price == 100.0
        assert signal.quantity == 1.0
        assert signal.metadata == {}

    def test_signal_with_metadata(self):
        """Test Signal with metadata."""
        metadata = {"indicator": "RSI", "value": 25.5}
        signal = Signal(
            date=pd.Timestamp("2023-01-01"),
            type=SignalType.SELL,
            price=101.0,
            quantity=2.0,
            metadata=metadata
        )

        assert signal.metadata == metadata

    def test_signal_type_from_int(self):
        """Test Signal type conversion from int."""
        signal = Signal(
            date=pd.Timestamp("2023-01-01"),
            type=1,
            price=100.0
        )

        assert signal.type == SignalType.BUY

    def test_signal_default_quantity(self):
        """Test Signal default quantity."""
        signal = Signal(
            date=pd.Timestamp("2023-01-01"),
            type=SignalType.HOLD,
            price=100.0
        )

        assert signal.quantity == 1.0

    def test_signal_repr(self):
        """Test Signal string representation."""
        signal = Signal(
            date=pd.Timestamp("2023-01-01"),
            type=SignalType.BUY,
            price=100.0
        )

        repr_str = repr(signal)
        assert "Signal" in repr_str
        assert "BUY" in repr_str
        assert "100.0" in repr_str


class TestStrategyConfig:
    """Tests for StrategyConfig dataclass."""

    def test_config_default_values(self):
        """Test StrategyConfig with default values."""
        config = StrategyConfig()

        assert config.name == "BaseStrategy"
        assert config.description == ""

    def test_config_custom_values(self):
        """Test StrategyConfig with custom values."""
        config = StrategyConfig(
            name="TestStrategy",
            description="A test strategy"
        )

        assert config.name == "TestStrategy"
        assert config.description == "A test strategy"

    def test_config_validate(self):
        """Test StrategyConfig validation."""
        config = StrategyConfig()
        assert config.validate() is True

    def test_config_repr(self):
        """Test StrategyConfig string representation."""
        config = StrategyConfig(name="MyStrategy")
        repr_str = repr(config)

        assert "MyStrategy" in repr_str


class MockStrategy(BaseStrategy):
    """Mock strategy for testing BaseStrategy."""

    def __init__(self, config=None, min_periods=20):
        super().__init__(config)
        self._min_periods = min_periods

    @property
    def required_columns(self):
        return ["close"]

    @property
    def min_periods(self):
        return self._min_periods

    def _compute_signals(self, data):
        close = data["close"]
        signals = np.zeros(len(close))
        signals[close > 100] = 1
        signals[close < 90] = -1
        return signals


class TestBaseStrategy:
    """Tests for BaseStrategy class."""

    @pytest.fixture
    def strategy(self):
        """Create BaseStrategy instance."""
        return MockStrategy()

    @pytest.fixture
    def custom_config(self):
        """Create custom configuration."""
        return StrategyConfig(name="CustomStrategy", description="Custom desc")

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data."""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 2)

        return pd.DataFrame({
            "open": prices + 0.5,
            "high": prices + 2,
            "low": prices - 2,
            "close": prices,
            "volume": np.random.randint(1000000, 5000000, 50)
        }, index=dates)

    def test_init_default_config(self, strategy):
        """Test initialization with default config."""
        assert strategy.name == "BaseStrategy"
        assert isinstance(strategy.config, StrategyConfig)

    def test_init_custom_config(self, custom_config):
        """Test initialization with custom config."""
        strategy = MockStrategy(custom_config)

        assert strategy.name == "CustomStrategy"
        assert strategy.config.description == "Custom desc"

    def test_required_columns(self, strategy):
        """Test required_columns property."""
        assert strategy.required_columns == ["close"]

    def test_required_indicators_default(self, strategy):
        """Test required_indicators with default value."""
        assert strategy.required_indicators == []

    def test_validate_data_success(self, strategy, sample_data):
        """Test validate_data with valid data."""
        strategy.validate_data(sample_data)

    def test_validate_data_missing_columns(self, strategy):
        """Test validate_data with missing columns raises error."""
        invalid_data = pd.DataFrame({"open": [100, 101, 102]})

        with pytest.raises(ValueError, match="Missing required columns"):
            strategy.validate_data(invalid_data)

    def test_validate_data_insufficient_data(self, strategy, sample_data):
        """Test validate_data with insufficient data raises error."""
        short_data = sample_data.head(5)

        with pytest.raises(ValueError, match="Insufficient data"):
            strategy.validate_data(short_data)

    def test_min_periods_property(self, strategy):
        """Test min_periods property."""
        assert strategy.min_periods == 20

    def test_min_periods_custom(self):
        """Test min_periods with custom value."""
        strategy = MockStrategy(min_periods=50)
        assert strategy.min_periods == 50

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
        small_data = pd.DataFrame({"close": [100, 101, 102]})

        with pytest.raises(ValueError, match="Insufficient data"):
            strategy.generate_signals(small_data)

    def test_generate_signals_with_missing_columns(self, strategy):
        """Test with missing columns raises error."""
        incomplete_data = pd.DataFrame({"open": [100, 101, 102]})

        with pytest.raises(ValueError, match="Missing required columns"):
            strategy.generate_signals(incomplete_data)

    def test_generate_signals_invalid_signal_length(self):
        """Test with invalid signal length raises error."""
        class BadStrategy(MockStrategy):
            def _compute_signals(self, data):
                return np.array([1, -1])

        strategy = BadStrategy(min_periods=1)
        data = pd.DataFrame({"close": [100, 101, 102, 103, 104]})

        with pytest.raises(ValueError, match="Signal length"):
            strategy.generate_signals(data)

    def test_generate_signals_invalid_signal_values(self):
        """Test with invalid signal values raises error."""
        class BadStrategy(MockStrategy):
            def _compute_signals(self, data):
                return np.array([1, 0, 2, -1, 0])

        strategy = BadStrategy(min_periods=1)
        data = pd.DataFrame({"close": [100, 101, 102, 103, 104]})

        with pytest.raises(ValueError, match="Invalid signal values"):
            strategy.generate_signals(data)

    def test_get_indicator(self, strategy, sample_data):
        """Test get_indicator returns None when not set."""
        indicator = strategy.get_indicator("rsi")
        assert indicator is None

    def test_get_signals_empty(self, strategy, sample_data):
        """Test get_signals returns empty list initially."""
        strategy.generate_signals(sample_data)
        signals = strategy.get_signals()

        assert isinstance(signals, list)

    def test_get_parameters(self, strategy):
        """Test get_parameters returns dict."""
        params = strategy.get_parameters()
        assert isinstance(params, dict)

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)
        assert "MockStrategy" in repr_str


class TestBaseStrategyEdgeCases:
    """Edge case tests for BaseStrategy."""

    def test_validate_data_empty_dataframe(self):
        """Test validate_data with empty DataFrame."""
        strategy = MockStrategy()
        empty_data = pd.DataFrame(columns=["close"])

        with pytest.raises(ValueError):
            strategy.validate_data(empty_data)

    def test_validate_data_with_extra_columns(self, sample_ohlcv_data):
        """Test validate_data with extra columns passes."""
        strategy = MockStrategy()
        extra_data = sample_ohlcv_data.copy()
        extra_data["extra_column"] = 123

        strategy.validate_data(extra_data)

    def test_generate_signals_resets_state(self, sample_ohlcv_data):
        """Test that generate_signals resets internal state."""
        strategy = MockStrategy()

        signals1 = strategy.generate_signals(sample_ohlcv_data)
        signals2 = strategy.generate_signals(sample_ohlcv_data)

        assert len(signals1) == len(signals2)
        np.testing.assert_array_equal(signals1, signals2)
