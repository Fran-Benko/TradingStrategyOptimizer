"""
Unit tests for Pairs Trading strategy.
"""

import pytest
import pandas as pd
import numpy as np

from trading_system.strategies.arbitrage.pairs_trading_strategy import (
    PairsTradingStrategy,
    PairsTradingConfig,
    BollingerBandsPairsStrategy,
)


class TestPairsTradingConfig:
    """Tests for PairsTradingConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PairsTradingConfig()
        
        assert config.lookback_period == 60
        assert config.zscore_window == 20
        assert config.entry_threshold == 2.0
        assert config.exit_threshold == 0.5
        assert config.stop_loss_threshold == 3.0
        assert config.hedge_method == "rolling"
        assert config.kalman_gain == 0.001
        assert config.num_standard_deviations == 2.0
        assert config.spread_method == "log"

    def test_custom_config(self):
        """Test custom configuration."""
        config = PairsTradingConfig(
            lookback_period=30,
            zscore_window=10,
            entry_threshold=1.5,
            exit_threshold=0.3,
            stop_loss_threshold=2.5,
            hedge_method="static",
            kalman_gain=0.005,
            spread_method="simple"
        )
        
        assert config.lookback_period == 30
        assert config.zscore_window == 10
        assert config.entry_threshold == 1.5
        assert config.exit_threshold == 0.3
        assert config.stop_loss_threshold == 2.5
        assert config.hedge_method == "static"
        assert config.kalman_gain == 0.005
        assert config.spread_method == "simple"

    def test_config_validation_lookback_too_low(self):
        """Test validation fails when lookback < 10."""
        with pytest.raises(ValueError, match="Lookback period must be between 10 and 500"):
            PairsTradingConfig(lookback_period=5)

    def test_config_validation_lookback_too_high(self):
        """Test validation fails when lookback > 500."""
        with pytest.raises(ValueError, match="Lookback period must be between 10 and 500"):
            PairsTradingConfig(lookback_period=501)

    def test_config_validation_zscore_window_too_low(self):
        """Test validation fails when zscore_window < 5."""
        with pytest.raises(ValueError, match="Z-score window must be between 5 and 100"):
            PairsTradingConfig(zscore_window=3)

    def test_config_validation_zscore_window_too_high(self):
        """Test validation fails when zscore_window > 100."""
        with pytest.raises(ValueError, match="Z-score window must be between 5 and 100"):
            PairsTradingConfig(zscore_window=101)

    def test_config_validation_entry_threshold_too_low(self):
        """Test validation fails when entry_threshold < 0.1."""
        with pytest.raises(ValueError, match="Entry threshold must be between 0.1 and 5.0"):
            PairsTradingConfig(entry_threshold=0.05)

    def test_config_validation_entry_threshold_too_high(self):
        """Test validation fails when entry_threshold > 5.0."""
        with pytest.raises(ValueError, match="Entry threshold must be between 0.1 and 5.0"):
            PairsTradingConfig(entry_threshold=6.0)

    def test_config_validation_exit_threshold_negative(self):
        """Test validation fails when exit_threshold < 0."""
        with pytest.raises(ValueError, match="Exit threshold must be non-negative"):
            PairsTradingConfig(exit_threshold=-0.1)

    def test_config_validation_exit_greater_than_entry(self):
        """Test validation fails when exit_threshold >= entry_threshold."""
        with pytest.raises(ValueError, match="Exit threshold must be non-negative and less than entry"):
            PairsTradingConfig(entry_threshold=2.0, exit_threshold=2.5)

    def test_config_validation_stop_loss_less_than_entry(self):
        """Test validation fails when stop_loss <= entry."""
        with pytest.raises(ValueError, match="Stop loss threshold must be greater than entry"):
            PairsTradingConfig(entry_threshold=2.0, stop_loss_threshold=1.5)

    def test_config_validation_invalid_hedge_method(self):
        """Test validation fails for invalid hedge method."""
        with pytest.raises(ValueError, match="Hedge method must be"):
            PairsTradingConfig(hedge_method="invalid")

    def test_config_validation_invalid_spread_method(self):
        """Test validation fails for invalid spread method."""
        with pytest.raises(ValueError, match="Spread method must be"):
            PairsTradingConfig(spread_method="invalid")

    def test_config_validation_kalman_gain_too_low(self):
        """Test validation fails when kalman_gain <= 0."""
        with pytest.raises(ValueError, match="Kalman gain must be between 0 and 0.1"):
            PairsTradingConfig(kalman_gain=0)

    def test_config_validation_kalman_gain_too_high(self):
        """Test validation fails when kalman_gain > 0.1."""
        with pytest.raises(ValueError, match="Kalman gain must be between 0 and 0.1"):
            PairsTradingConfig(kalman_gain=0.15)


class TestPairsTradingStrategy:
    """Tests for PairsTradingStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create Pairs Trading strategy instance."""
        return PairsTradingStrategy()

    @pytest.fixture
    def custom_strategy(self):
        """Create Pairs Trading strategy with custom config."""
        config = PairsTradingConfig(
            lookback_period=30,
            zscore_window=10,
            entry_threshold=1.5,
            exit_threshold=0.3
        )
        return PairsTradingStrategy(config)

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data for pairs."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        base = 100 + np.cumsum(np.random.randn(100) * 2)
        correlated = base + np.random.randn(100) * 0.5

        return pd.DataFrame({
            "open": base + np.random.randn(100) * 0.5,
            "high": base + abs(np.random.randn(100)) * 2,
            "low": base - abs(np.random.randn(100)) * 2,
            "close": base,
            "close_0": base,
            "close_1": correlated,
            "volume": np.random.randint(1000000, 5000000, 100)
        }, index=dates)

    @pytest.fixture
    def sample_data_two_columns(self):
        """Generate sample data with two price columns."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        base = 100 + np.cumsum(np.random.randn(100) * 2)
        correlated = base + np.random.randn(100) * 0.5

        return pd.DataFrame({
            "price_0": base,
            "price_1": correlated
        }, index=dates)

    def test_init_default_config(self, strategy):
        """Test initialization with default config."""
        assert strategy.lookback_period == 60
        assert strategy.zscore_window == 20
        assert strategy.entry_threshold == 2.0
        assert strategy.exit_threshold == 0.5
        assert strategy.stop_loss_threshold == 3.0
        assert strategy.hedge_method == "rolling"

    def test_init_custom_config(self, custom_strategy):
        """Test initialization with custom config."""
        assert custom_strategy.lookback_period == 30
        assert custom_strategy.zscore_window == 10
        assert custom_strategy.entry_threshold == 1.5

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert strategy.required_columns == ["close_0", "close_1"]

    def test_min_periods(self, strategy):
        """Test minimum periods calculation."""
        # min_periods = max(lookback_period, zscore_window) = max(60, 20) = 60
        assert strategy.min_periods == 60

    def test_min_periods_custom(self, custom_strategy):
        """Test min periods with custom config."""
        # min_periods = max(lookback_period, zscore_window) = max(30, 10) = 30
        assert custom_strategy.min_periods == 30

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
            "close_0": [100, 101],
            "close_1": [50, 51]
        })

        with pytest.raises(ValueError, match="Insufficient data"):
            strategy.generate_signals(small_data)

    def test_generate_signals_with_close_columns(self, strategy, sample_data):
        """Test signals generation with close_0 and close_1 columns."""
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)
        assert set(signals).issubset({-1, 0, 1})

    def test_generate_signals_with_two_columns(self, strategy, sample_data_two_columns):
        """Test signals generation with two numeric columns."""
        signals = strategy.generate_signals(sample_data_two_columns)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data_two_columns)
        assert set(signals).issubset({-1, 0, 1})

    def test_generate_signals_with_single_close(self, strategy):
        """Test signals generation with single close column (backward compat)."""
        data = pd.DataFrame({
            "close": [100, 102, 101, 103, 102] + [100 + i for i in range(60)]
        })

        signals = strategy.generate_signals(data)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(data)

    def test_get_indicator_spread(self, strategy, sample_data):
        """Test getting spread indicator."""
        strategy.generate_signals(sample_data)

        spread = strategy.get_indicator("spread")

        assert spread is not None
        assert len(spread) == len(sample_data)

    def test_get_indicator_hedge_ratio(self, strategy, sample_data):
        """Test getting hedge ratio indicator."""
        strategy.generate_signals(sample_data)

        hedge_ratio = strategy.get_indicator("hedge_ratio")

        assert hedge_ratio is not None
        assert len(hedge_ratio) == len(sample_data)

    def test_get_indicator_zscore(self, strategy, sample_data):
        """Test getting zscore indicator."""
        strategy.generate_signals(sample_data)

        zscore = strategy.get_indicator("zscore")

        assert zscore is not None
        assert len(zscore) == len(sample_data)

    def test_get_indicator_nonexistent(self, strategy, sample_data):
        """Test getting nonexistent indicator returns None."""
        strategy.generate_signals(sample_data)

        indicator = strategy.get_indicator("nonexistent")

        assert indicator is None

    def test_get_parameters(self, strategy):
        """Test getting strategy parameters."""
        params = strategy.get_parameters()

        assert "lookback_period" in params
        assert "zscore_window" in params
        assert "entry_threshold" in params
        assert "hedge_method" in params
        assert params["lookback_period"] == 60

    def test_get_spread_statistics(self, strategy, sample_data):
        """Test getting spread statistics."""
        strategy.generate_signals(sample_data)

        stats = strategy.get_spread_statistics()

        assert "current_spread" in stats or stats == {}
        assert "spread_mean" in stats or stats == {}
        assert "spread_std" in stats or stats == {}

    def test_compute_spread_log_method(self, strategy):
        """Test spread calculation with log method."""
        prices1 = pd.Series([100, 102, 101, 103, 102])
        prices2 = pd.Series([50, 51, 50.5, 52, 51])

        spread, hedge_ratio = strategy._compute_spread(prices1, prices2)

        assert spread is not None
        assert len(spread) == len(prices1)

    def test_compute_spread_simple_method(self):
        """Test spread calculation with simple method."""
        config = PairsTradingConfig(spread_method="simple")
        strategy = PairsTradingStrategy(config)

        prices1 = pd.Series([100, 102, 101, 103, 102])
        prices2 = pd.Series([50, 51, 50.5, 52, 51])

        spread, hedge_ratio = strategy._compute_spread(prices1, prices2)

        assert spread is not None
        assert len(spread) == len(prices1)

    def test_compute_spread_ratio_method(self):
        """Test spread calculation with ratio method."""
        config = PairsTradingConfig(spread_method="ratio")
        strategy = PairsTradingStrategy(config)

        prices1 = pd.Series([100, 102, 101, 103, 102])
        prices2 = pd.Series([50, 51, 50.5, 52, 51])

        spread, hedge_ratio = strategy._compute_spread(prices1, prices2)

        assert spread is not None
        assert len(spread) == len(prices1)

    def test_calculate_static_hedge_ratio(self, strategy):
        """Test static hedge ratio calculation."""
        prices1 = pd.Series([100, 102, 101, 103, 102, 104, 103, 105, 104, 106] * 6)
        prices2 = pd.Series([50, 51, 50.5, 52, 51, 52.5, 52, 53, 52.5, 53.5] * 6)

        hedge_ratio = strategy._calculate_static_hedge_ratio(prices1, prices2)

        assert hedge_ratio is not None

    def test_calculate_rolling_hedge_ratio(self, strategy):
        """Test rolling hedge ratio calculation."""
        prices1 = pd.Series([100, 102, 101, 103, 102] * 12)
        prices2 = pd.Series([50, 51, 50.5, 52, 51] * 12)

        hedge_ratio = strategy._calculate_rolling_hedge_ratio(prices1, prices2)

        assert hedge_ratio is not None
        assert len(hedge_ratio) == len(prices1)

    def test_calculate_kalman_hedge_ratio(self):
        """Test Kalman filter hedge ratio calculation."""
        config = PairsTradingConfig(hedge_method="kalman")
        strategy = PairsTradingStrategy(config)

        prices1 = pd.Series([100, 102, 101, 103, 102] * 12)
        prices2 = pd.Series([50, 51, 50.5, 52, 51] * 12)

        hedge_ratio = strategy._calculate_kalman_hedge_ratio(prices1, prices2)

        assert hedge_ratio is not None
        assert len(hedge_ratio) == len(prices1)

    def test_calculate_zscore(self, strategy):
        """Test z-score calculation."""
        spread = pd.Series([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])

        zscore = strategy._calculate_zscore(spread)

        assert zscore is not None
        assert len(zscore) == len(spread)

    def test_calculate_zscore_handles_zero_std(self, strategy):
        """Test z-score handles zero standard deviation."""
        constant_spread = pd.Series([1.0] * 30)

        zscore = strategy._calculate_zscore(constant_spread)

        # Should handle zero std without raising
        assert zscore is not None

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "PairsTradingStrategy" in repr_str
        assert "lookback_period" in repr_str


class TestBollingerBandsPairsStrategy:
    """Tests for BollingerBandsPairsStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create Bollinger Bands Pairs Trading strategy instance."""
        return BollingerBandsPairsStrategy()

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data for pairs."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        base = 100 + np.cumsum(np.random.randn(100) * 2)
        correlated = base + np.random.randn(100) * 0.5

        return pd.DataFrame({
            "close_0": base,
            "close_1": correlated,
        }, index=dates)

    def test_init(self, strategy):
        """Test initialization."""
        assert strategy.lookback_period == 60
        assert strategy.entry_threshold == 2.0
        assert strategy.exit_threshold == 0.5
        assert strategy.num_standard_deviations == 2.0

    def test_init_custom(self):
        """Test initialization with custom parameters."""
        strategy = BollingerBandsPairsStrategy(
            lookback_period=30,
            entry_threshold=1.5,
            exit_threshold=0.3,
            num_std=2.5
        )

        assert strategy.lookback_period == 30
        assert strategy.entry_threshold == 1.5
        assert strategy.exit_threshold == 0.3
        assert strategy.num_standard_deviations == 2.5

    def test_generate_signals_returns_array(self, strategy, sample_data):
        """Test that generate_signals returns numpy array."""
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)

    def test_generate_signals_values(self, strategy, sample_data):
        """Test that signals are valid (-1, 0, 1)."""
        signals = strategy.generate_signals(sample_data)

        assert set(signals).issubset({-1, 0, 1})

    def test_get_indicator_upper_band(self, strategy, sample_data):
        """Test getting upper band indicator."""
        strategy.generate_signals(sample_data)

        upper_band = strategy.get_indicator("upper_band")

        assert upper_band is not None

    def test_get_indicator_lower_band(self, strategy, sample_data):
        """Test getting lower band indicator."""
        strategy.generate_signals(sample_data)

        lower_band = strategy.get_indicator("lower_band")

        assert lower_band is not None

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "BollingerBandsPairsStrategy" in repr_str


class TestPairsTradingEdgeCases:
    """Edge case tests for Pairs Trading Strategy."""

    def test_identical_prices(self):
        """Test strategy with identical price series."""
        prices = pd.DataFrame({
            "close_0": [100.0] * 80,
            "close_1": [100.0] * 80
        })

        strategy = PairsTradingStrategy()
        signals = strategy.generate_signals(prices)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(prices)

    def test_highly_correlated_prices(self):
        """Test strategy with highly correlated prices."""
        np.random.seed(42)
        base = np.cumsum(np.random.randn(100))
        correlated = base * 1.2 + 10

        prices = pd.DataFrame({
            "close_0": base,
            "close_1": correlated
        })

        strategy = PairsTradingStrategy()
        signals = strategy.generate_signals(prices)

        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})

    def test_inversely_correlated_prices(self):
        """Test strategy with inversely correlated prices."""
        np.random.seed(42)
        base = np.cumsum(np.random.randn(100))
        inverse = -base

        prices = pd.DataFrame({
            "close_0": base,
            "close_1": inverse
        })

        strategy = PairsTradingStrategy()
        signals = strategy.generate_signals(prices)

        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})
