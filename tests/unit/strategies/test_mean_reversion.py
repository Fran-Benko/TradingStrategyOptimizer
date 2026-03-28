"""
Unit tests for Mean Reversion strategy.
"""

import pytest
import pandas as pd
import numpy as np

from trading_system.strategies.mean_reversion.mean_reversion_strategy import (
    MeanReversionStrategy,
    MeanReversionConfig,
)


class TestMeanReversionConfig:
    """Tests for MeanReversionConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MeanReversionConfig()
        
        assert config.lookback_period == 20
        assert config.entry_threshold == -2.0
        assert config.exit_threshold == 0.0
        assert config.use_stochastic_entry is False
        assert config.use_adaptive_thresholds is False
        assert config.position_size == 1.0
        assert config.max_position_hold == 0

    def test_custom_config(self):
        """Test custom configuration."""
        config = MeanReversionConfig(
            lookback_period=30,
            entry_threshold=-1.5,
            exit_threshold=0.5,
            use_stochastic_entry=True,
            use_adaptive_thresholds=True,
            position_size=0.5,
            max_position_hold=10
        )
        
        assert config.lookback_period == 30
        assert config.entry_threshold == -1.5
        assert config.exit_threshold == 0.5
        assert config.use_stochastic_entry is True
        assert config.use_adaptive_thresholds is True
        assert config.position_size == 0.5
        assert config.max_position_hold == 10

    def test_config_validation_lookback_too_low(self):
        """Test validation fails when lookback < 5."""
        with pytest.raises(ValueError, match="Lookback period must be between 5 and 500"):
            MeanReversionConfig(lookback_period=4)

    def test_config_validation_lookback_too_high(self):
        """Test validation fails when lookback > 500."""
        with pytest.raises(ValueError, match="Lookback period must be between 5 and 500"):
            MeanReversionConfig(lookback_period=501)

    def test_config_validation_entry_threshold_too_high(self):
        """Test validation fails when entry_threshold > -0.1."""
        with pytest.raises(ValueError, match="Entry threshold must be between -5.0 and -0.1"):
            MeanReversionConfig(entry_threshold=0.0)

    def test_config_validation_entry_threshold_too_low(self):
        """Test validation fails when entry_threshold < -5.0."""
        with pytest.raises(ValueError, match="Entry threshold must be between -5.0 and -0.1"):
            MeanReversionConfig(entry_threshold=-5.5)

    def test_config_validation_exit_threshold_out_of_range(self):
        """Test validation fails when exit_threshold out of range."""
        with pytest.raises(ValueError, match="Exit threshold must be between -3.0 and 3.0"):
            MeanReversionConfig(exit_threshold=5.0)

    def test_config_validation_entry_greater_than_exit(self):
        """Test validation fails when entry_threshold >= exit_threshold."""
        with pytest.raises(ValueError, match="Entry threshold must be less than exit threshold"):
            MeanReversionConfig(entry_threshold=-1.0, exit_threshold=-2.0)

    def test_config_validation_position_size_zero(self):
        """Test validation fails when position_size <= 0."""
        with pytest.raises(ValueError, match="Position size must be positive"):
            MeanReversionConfig(position_size=0)

    def test_config_validation_max_position_hold_negative(self):
        """Test validation fails when max_position_hold < 0."""
        with pytest.raises(ValueError, match="Max position hold must be non-negative"):
            MeanReversionConfig(max_position_hold=-1)


class TestMeanReversionStrategy:
    """Tests for MeanReversionStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create Mean Reversion strategy instance."""
        return MeanReversionStrategy()

    @pytest.fixture
    def custom_strategy(self):
        """Create Mean Reversion strategy with custom config."""
        config = MeanReversionConfig(
            lookback_period=30,
            entry_threshold=-1.5,
            exit_threshold=0.5
        )
        return MeanReversionStrategy(config)

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
        assert strategy.lookback_period == 20
        assert strategy.entry_threshold == -2.0
        assert strategy.exit_threshold == 0.0
        assert strategy.use_stochastic_entry is False
        assert strategy.use_adaptive_thresholds is False

    def test_init_custom_config(self, custom_strategy):
        """Test initialization with custom config."""
        assert custom_strategy.lookback_period == 30
        assert custom_strategy.entry_threshold == -1.5
        assert custom_strategy.exit_threshold == 0.5

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert strategy.required_columns == ["close"]

    def test_min_periods(self, strategy):
        """Test minimum periods calculation."""
        # min_periods = lookback_period + 2 = 20 + 2 = 22
        assert strategy.min_periods == 22

    def test_min_periods_custom(self, custom_strategy):
        """Test min periods with custom config."""
        # min_periods = lookback_period + 2 = 30 + 2 = 32
        assert custom_strategy.min_periods == 32

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

    def test_get_indicator_z_score(self, strategy, sample_data):
        """Test getting z-score indicator."""
        strategy.generate_signals(sample_data)

        z_score = strategy.get_indicator("z_score")

        assert z_score is not None
        assert len(z_score) == len(sample_data)

    def test_get_indicator_rolling_mean(self, strategy, sample_data):
        """Test getting rolling mean indicator."""
        strategy.generate_signals(sample_data)

        rolling_mean = strategy.get_indicator("rolling_mean")

        assert rolling_mean is not None
        assert len(rolling_mean) == len(sample_data)

    def test_get_indicator_rolling_std(self, strategy, sample_data):
        """Test getting rolling std indicator."""
        strategy.generate_signals(sample_data)

        rolling_std = strategy.get_indicator("rolling_std")

        assert rolling_std is not None
        assert len(rolling_std) == len(sample_data)

    def test_get_indicator_nonexistent(self, strategy, sample_data):
        """Test getting nonexistent indicator returns None."""
        strategy.generate_signals(sample_data)

        indicator = strategy.get_indicator("nonexistent")

        assert indicator is None

    def test_get_parameters(self, strategy):
        """Test getting strategy parameters."""
        params = strategy.get_parameters()

        assert "lookback_period" in params
        assert "entry_threshold" in params
        assert "exit_threshold" in params
        assert params["lookback_period"] == 20

    def test_should_enter_z_score_below_threshold(self, strategy):
        """Test _should_enter returns True when z-score is below threshold."""
        # entry_threshold = -2.0, so -3.0 should trigger entry
        assert strategy._should_enter(z_score=-3.0, index=10, close=pd.Series([100])) is True

    def test_should_enter_z_score_above_threshold(self, strategy):
        """Test _should_enter returns False when z-score is above threshold."""
        # entry_threshold = -2.0, so -1.0 should not trigger entry
        assert strategy._should_enter(z_score=-1.0, index=10, close=pd.Series([100])) is False

    def test_should_enter_z_score_at_threshold(self, strategy):
        """Test _should_enter at exact threshold."""
        # entry_threshold = -2.0, so -2.0 should not trigger entry (needs to be less)
        assert strategy._should_enter(z_score=-2.0, index=10, close=pd.Series([100])) is False

    def test_should_enter_with_stochastic_entry(self):
        """Test _should_enter with stochastic confirmation enabled."""
        config = MeanReversionConfig(use_stochastic_entry=True)
        strategy = MeanReversionStrategy(config)
        
        # Generate data to populate stochastic indicator
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        data = pd.DataFrame({
            "close": 100 + np.cumsum(np.random.randn(50) * 2)
        }, index=dates)
        
        # Calculate stochastic
        stochastic = strategy._calculate_stochastic(data["close"])
        strategy._indicators["stochastic"] = stochastic
        
        # Z-score below threshold but stochastic not oversold (< 20)
        # Should return False
        assert not strategy._should_enter(
            z_score=-3.0,
            index=30,  # Index where stochastic is available
            close=data["close"]
        )

    def test_calculate_stochastic(self, strategy, sample_data):
        """Test stochastic calculation."""
        stochastic = strategy._calculate_stochastic(sample_data["close"])

        assert stochastic is not None
        assert len(stochastic) == len(sample_data)
        valid_stochastic = stochastic[stochastic.notna()]
        assert (valid_stochastic >= 0).all()
        assert (valid_stochastic <= 100).all()

    def test_calculate_adaptive_thresholds(self, strategy, sample_data):
        """Test adaptive threshold calculation."""
        # First generate z_score indicator
        close = sample_data["close"]
        rolling_std = close.rolling(window=strategy.lookback_period).std()
        z_score = (close - close.rolling(window=strategy.lookback_period).mean()) / rolling_std
        
        entry, exit_threshold = strategy._calculate_adaptive_thresholds(z_score, rolling_std)

        assert entry is not None
        assert exit_threshold is not None

    def test_generate_signals_with_adaptive_thresholds(self, sample_data):
        """Test signals with adaptive thresholds enabled."""
        config = MeanReversionConfig(use_adaptive_thresholds=True)
        strategy = MeanReversionStrategy(config)
        
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)
        assert set(signals).issubset({-1, 0, 1})

    def test_generate_signals_with_max_position_hold(self, sample_data):
        """Test signals with max position hold limit."""
        config = MeanReversionConfig(max_position_hold=5)
        strategy = MeanReversionStrategy(config)
        
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)
        assert set(signals).issubset({-1, 0, 1})

    def test_z_score_calculation(self, sample_data):
        """Test z-score is calculated correctly."""
        strategy = MeanReversionStrategy()
        strategy.generate_signals(sample_data)
        
        z_score = strategy.get_indicator("z_score")
        rolling_mean = strategy.get_indicator("rolling_mean")
        rolling_std = strategy.get_indicator("rolling_std")
        
        # Calculate expected z-score manually for valid indices
        valid_idx = strategy.lookback_period
        expected_z = (sample_data["close"].iloc[valid_idx] - rolling_mean.iloc[valid_idx]) / rolling_std.iloc[valid_idx]
        
        assert abs(z_score.iloc[valid_idx] - expected_z) < 0.01

    def test_z_score_handles_infinite_values(self, sample_data):
        """Test z-score handles infinite values from division by zero."""
        # Create data with constant values (rolling_std = 0)
        constant_data = pd.DataFrame({
            "close": [100.0] * 50
        })
        
        strategy = MeanReversionStrategy()
        signals = strategy.generate_signals(constant_data)
        
        # Should not raise, should return valid signals
        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "MeanReversionStrategy" in repr_str
        assert "lookback_period" in repr_str


class TestMeanReversionEdgeCases:
    """Edge case tests for Mean Reversion Strategy."""

    def test_constant_price_data(self):
        """Test strategy with constant price data."""
        data = pd.DataFrame({
            "close": [100.0] * 100
        })
        
        strategy = MeanReversionStrategy()
        signals = strategy.generate_signals(data)
        
        # Should not raise, z-score should be 0 where std is 0
        assert isinstance(signals, np.ndarray)

    def test_high_volatility_data(self):
        """Test strategy with high volatility data."""
        np.random.seed(42)
        prices = [100]
        for _ in range(99):
            prices.append(prices[-1] + np.random.randn() * 10)  # High volatility
        
        data = pd.DataFrame({"close": prices})
        
        strategy = MeanReversionStrategy()
        signals = strategy.generate_signals(data)
        
        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})

    def test_trending_data(self):
        """Test strategy with strongly trending data."""
        np.random.seed(42)
        # Strong upward trend
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5 + 0.5)
        
        data = pd.DataFrame({"close": prices})
        
        strategy = MeanReversionStrategy()
        signals = strategy.generate_signals(data)
        
        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})
