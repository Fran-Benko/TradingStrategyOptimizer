"""
Unit tests for ML-based strategies.
"""

import pytest
import pandas as pd
import numpy as np

from trading_system.strategies.ml_based.trend_classifier_strategy import (
    TrendClassifierStrategy,
    TrendClassifierConfig,
    TrendType,
    AdaptiveTrendStrategy,
)
from trading_system.strategies.ml_based.momentum_ml_strategy import (
    MomentumMLStrategy,
    MomentumMLConfig,
    SimpleMomentumStrategy,
)


# =============================================================================
# Trend Classifier Strategy Tests
# =============================================================================

class TestTrendClassifierConfig:
    """Tests for TrendClassifierConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TrendClassifierConfig()
        
        assert config.fast_period == 10
        assert config.slow_period == 30
        assert config.signal_period == 5
        assert config.uptrend_threshold == 0.02
        assert config.downtrend_threshold == -0.02
        assert config.require_confirmation is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = TrendClassifierConfig(
            fast_period=5,
            slow_period=20,
            signal_period=3,
            uptrend_threshold=0.03,
            downtrend_threshold=-0.03,
            require_confirmation=False
        )
        
        assert config.fast_period == 5
        assert config.slow_period == 20
        assert config.signal_period == 3
        assert config.uptrend_threshold == 0.03
        assert config.downtrend_threshold == -0.03
        assert config.require_confirmation is False

    def test_config_validation_fast_period_too_low(self):
        """Test validation fails when fast_period < 2."""
        with pytest.raises(ValueError, match="Fast period must be between 2 and 100"):
            TrendClassifierConfig(fast_period=1)

    def test_config_validation_fast_period_too_high(self):
        """Test validation fails when fast_period > 100."""
        with pytest.raises(ValueError, match="Fast period must be between 2 and 100"):
            TrendClassifierConfig(fast_period=101)

    def test_config_validation_slow_period_too_low(self):
        """Test validation fails when slow_period < 5."""
        with pytest.raises(ValueError, match="Slow period must be between 5 and 500"):
            TrendClassifierConfig(slow_period=3)

    def test_config_validation_fast_greater_than_slow(self):
        """Test validation fails when fast_period >= slow_period."""
        with pytest.raises(ValueError, match="Fast period must be less than slow period"):
            TrendClassifierConfig(fast_period=20, slow_period=10)

    def test_config_validation_signal_period_invalid(self):
        """Test validation fails when signal_period out of range."""
        with pytest.raises(ValueError, match="Signal period must be between 1 and 50"):
            TrendClassifierConfig(signal_period=0)

    def test_config_validation_uptrend_threshold_range(self):
        """Test validation fails for invalid uptrend threshold."""
        with pytest.raises(ValueError, match="Uptrend threshold must be between -1 and 1"):
            TrendClassifierConfig(uptrend_threshold=2.0)

    def test_config_validation_downtrend_threshold_range(self):
        """Test validation fails for invalid downtrend threshold."""
        with pytest.raises(ValueError, match="Downtrend threshold must be between -1 and 1"):
            TrendClassifierConfig(downtrend_threshold=-2.0)

    def test_config_validation_threshold_order(self):
        """Test validation fails when uptrend <= downtrend."""
        with pytest.raises(ValueError, match="Uptrend threshold must be greater than downtrend"):
            TrendClassifierConfig(uptrend_threshold=0.01, downtrend_threshold=0.02)


class TestTrendClassifierStrategy:
    """Tests for TrendClassifierStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create Trend Classifier strategy instance."""
        return TrendClassifierStrategy()

    @pytest.fixture
    def custom_strategy(self):
        """Create Trend Classifier strategy with custom config."""
        config = TrendClassifierConfig(
            fast_period=5,
            slow_period=20,
            signal_period=3,
            require_confirmation=False
        )
        return TrendClassifierStrategy(config)

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
        assert strategy.fast_period == 10
        assert strategy.slow_period == 30
        assert strategy.signal_period == 5
        assert strategy.uptrend_threshold == 0.02
        assert strategy.downtrend_threshold == -0.02
        assert strategy.require_confirmation is True

    def test_init_custom_config(self, custom_strategy):
        """Test initialization with custom config."""
        assert custom_strategy.fast_period == 5
        assert custom_strategy.slow_period == 20
        assert custom_strategy.signal_period == 3

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert strategy.required_columns == ["close"]

    def test_min_periods(self, strategy):
        """Test minimum periods calculation."""
        # min_periods = slow_period + signal_period = 30 + 5 = 35
        assert strategy.min_periods == 35

    def test_min_periods_custom(self, custom_strategy):
        """Test min periods with custom config."""
        # min_periods = slow_period + signal_period = 20 + 3 = 23
        assert custom_strategy.min_periods == 23

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

    def test_get_current_trend_uptrend(self, strategy, sample_data):
        """Test getting current trend returns valid trend type."""
        trend = strategy.get_current_trend(sample_data)

        assert isinstance(trend, TrendType)
        assert trend in [TrendType.UPTREND, TrendType.DOWNTREND, TrendType.RANGING]

    def test_get_current_trend_consistency(self, strategy, sample_data):
        """Test trend detection is consistent."""
        trend1 = strategy.get_current_trend(sample_data)
        trend2 = strategy.get_current_trend(sample_data)

        assert trend1 == trend2

    def test_get_indicator_fast_ma(self, strategy, sample_data):
        """Test getting fast MA indicator."""
        strategy.generate_signals(sample_data)

        fast_ma = strategy.get_indicator("fast_ma")

        assert fast_ma is not None
        assert len(fast_ma) == len(sample_data)

    def test_get_indicator_slow_ma(self, strategy, sample_data):
        """Test getting slow MA indicator."""
        strategy.generate_signals(sample_data)

        slow_ma = strategy.get_indicator("slow_ma")

        assert slow_ma is not None
        assert len(slow_ma) == len(sample_data)

    def test_get_indicator_ma_diff(self, strategy, sample_data):
        """Test getting MA difference indicator."""
        strategy.generate_signals(sample_data)

        ma_diff = strategy.get_indicator("ma_diff")

        assert ma_diff is not None
        assert len(ma_diff) == len(sample_data)

    def test_get_indicator_nonexistent(self, strategy, sample_data):
        """Test getting nonexistent indicator returns None."""
        strategy.generate_signals(sample_data)

        indicator = strategy.get_indicator("nonexistent")

        assert indicator is None

    def test_generate_signals_no_confirmation(self):
        """Test signals generation without confirmation requirement."""
        config = TrendClassifierConfig(require_confirmation=False)
        strategy = TrendClassifierStrategy(config)
        
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        data = pd.DataFrame({"close": prices}, index=dates)
        
        signals = strategy.generate_signals(data)

        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})

    def test_generate_signals_with_confirmation(self, strategy, sample_data):
        """Test signals generation with confirmation requirement."""
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "TrendClassifierStrategy" in repr_str
        assert "fast_period" in repr_str


class TestAdaptiveTrendStrategy:
    """Tests for AdaptiveTrendStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create Adaptive Trend strategy instance."""
        return AdaptiveTrendStrategy()

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        prices = 100 + np.cumsum(np.random.randn(100) * 2)

        return pd.DataFrame({
            "close": prices,
        }, index=dates)

    def test_init(self, strategy):
        """Test initialization."""
        assert strategy.fast_period == 10
        assert strategy.slow_period == 30
        assert strategy.volatility_lookback == 20

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

    def test_get_indicator_adaptive_up(self, strategy, sample_data):
        """Test getting adaptive up threshold indicator."""
        strategy.generate_signals(sample_data)

        adaptive_up = strategy.get_indicator("adaptive_up")

        assert adaptive_up is not None


# =============================================================================
# Momentum ML Strategy Tests
# =============================================================================

class TestMomentumMLConfig:
    """Tests for MomentumMLConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MomentumMLConfig()
        
        assert config.feature_lookback == 20
        assert config.prediction_horizon == 5
        assert config.momentum_threshold == 0.01
        assert config.volatility_threshold == 0.02
        assert config.min_confidence == 0.6
        assert config.use_ml_model is True
        assert config.rsi_period == 14
        assert config.atr_period == 14

    def test_custom_config(self):
        """Test custom configuration."""
        config = MomentumMLConfig(
            feature_lookback=30,
            prediction_horizon=10,
            momentum_threshold=0.02,
            volatility_threshold=0.03,
            min_confidence=0.7,
            use_ml_model=False,
            rsi_period=10,
            atr_period=10
        )
        
        assert config.feature_lookback == 30
        assert config.prediction_horizon == 10
        assert config.momentum_threshold == 0.02
        assert config.volatility_threshold == 0.03
        assert config.min_confidence == 0.7
        assert config.use_ml_model is False
        assert config.rsi_period == 10
        assert config.atr_period == 10

    def test_config_validation_feature_lookback_too_low(self):
        """Test validation fails when feature_lookback < 5."""
        with pytest.raises(ValueError, match="Feature lookback must be between 5 and 100"):
            MomentumMLConfig(feature_lookback=3)

    def test_config_validation_feature_lookback_too_high(self):
        """Test validation fails when feature_lookback > 100."""
        with pytest.raises(ValueError, match="Feature lookback must be between 5 and 100"):
            MomentumMLConfig(feature_lookback=101)

    def test_config_validation_prediction_horizon_too_low(self):
        """Test validation fails when prediction_horizon < 1."""
        with pytest.raises(ValueError, match="Prediction horizon must be between 1 and 50"):
            MomentumMLConfig(prediction_horizon=0)

    def test_config_validation_prediction_horizon_too_high(self):
        """Test validation fails when prediction_horizon > 50."""
        with pytest.raises(ValueError, match="Prediction horizon must be between 1 and 50"):
            MomentumMLConfig(prediction_horizon=51)

    def test_config_validation_momentum_threshold_range(self):
        """Test validation fails for invalid momentum threshold."""
        with pytest.raises(ValueError, match="Momentum threshold must be between -1 and 1"):
            MomentumMLConfig(momentum_threshold=2.0)

    def test_config_validation_volatility_threshold_range(self):
        """Test validation fails for invalid volatility threshold."""
        with pytest.raises(ValueError, match="Volatility threshold must be between 0 and 1"):
            MomentumMLConfig(volatility_threshold=2.0)

    def test_config_validation_min_confidence_too_low(self):
        """Test validation fails when min_confidence < 0.1."""
        with pytest.raises(ValueError, match="Min confidence must be between 0.1 and 1.0"):
            MomentumMLConfig(min_confidence=0.05)

    def test_config_validation_min_confidence_too_high(self):
        """Test validation fails when min_confidence > 1.0."""
        with pytest.raises(ValueError, match="Min confidence must be between 0.1 and 1.0"):
            MomentumMLConfig(min_confidence=1.5)

    def test_config_validation_rsi_period_range(self):
        """Test validation fails for invalid RSI period."""
        with pytest.raises(ValueError, match="RSI period must be between 2 and 100"):
            MomentumMLConfig(rsi_period=1)

    def test_config_validation_atr_period_range(self):
        """Test validation fails for invalid ATR period."""
        with pytest.raises(ValueError, match="ATR period must be between 2 and 100"):
            MomentumMLConfig(atr_period=1)


class TestMomentumMLStrategy:
    """Tests for MomentumMLStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create Momentum ML strategy instance."""
        return MomentumMLStrategy()

    @pytest.fixture
    def custom_strategy(self):
        """Create Momentum ML strategy with custom config."""
        config = MomentumMLConfig(
            feature_lookback=30,
            prediction_horizon=10,
            use_ml_model=False
        )
        return MomentumMLStrategy(config)

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
        assert strategy.feature_lookback == 20
        assert strategy.prediction_horizon == 5
        assert strategy.momentum_threshold == 0.01
        assert strategy.min_confidence == 0.6
        assert strategy.use_ml_model is True

    def test_init_custom_config(self, custom_strategy):
        """Test initialization with custom config."""
        assert custom_strategy.feature_lookback == 30
        assert custom_strategy.prediction_horizon == 10
        assert custom_strategy.use_ml_model is False

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert "close" in strategy.required_columns
        assert "high" in strategy.required_columns
        assert "low" in strategy.required_columns

    def test_min_periods(self, strategy):
        """Test minimum periods calculation."""
        # min_periods = max(feature_lookback + prediction_horizon, rsi_period + 5, atr_period + 5)
        # = max(20 + 5, 14 + 5, 14 + 5) = max(25, 19, 19) = 25
        assert strategy.min_periods == 25

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
            "close": [100, 101, 102],
            "high": [102, 103, 104],
            "low": [98, 99, 100]
        })

        with pytest.raises(ValueError, match="Insufficient data"):
            strategy.generate_signals(small_data)

    def test_generate_signals_with_missing_columns(self, strategy):
        """Test with missing columns raises error."""
        incomplete_data = pd.DataFrame({"close": [100, 101, 102]})

        with pytest.raises(ValueError, match="Missing required columns"):
            strategy.generate_signals(incomplete_data)

    def test_generate_signals_rule_based(self):
        """Test signals generation without ML model."""
        config = MomentumMLConfig(use_ml_model=False)
        strategy = MomentumMLStrategy(config)
        
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        data = pd.DataFrame({
            "close": prices,
            "high": prices + abs(np.random.randn(100)) * 2,
            "low": prices - abs(np.random.randn(100)) * 2,
        }, index=dates)
        
        signals = strategy.generate_signals(data)

        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})

    def test_get_indicator_features(self, strategy, sample_data):
        """Test getting features indicator."""
        strategy.generate_signals(sample_data)

        features = strategy.get_indicator("features")

        assert features is not None
        assert isinstance(features, pd.DataFrame)
        assert len(features) == len(sample_data)

    def test_get_indicator_confidence(self, strategy, sample_data):
        """Test getting confidence indicator."""
        strategy.generate_signals(sample_data)

        confidence = strategy.get_indicator("confidence")

        assert confidence is not None
        assert len(confidence) == len(sample_data)
        assert (confidence >= 0).all()
        assert (confidence <= 1).all()

    def test_get_indicator_nonexistent(self, strategy, sample_data):
        """Test getting nonexistent indicator returns None."""
        strategy.generate_signals(sample_data)

        indicator = strategy.get_indicator("nonexistent")

        assert indicator is None

    def test_get_confidence(self, strategy, sample_data):
        """Test getting current confidence score."""
        confidence = strategy.get_confidence(sample_data)

        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1

    def test_create_features(self, strategy, sample_data):
        """Test feature creation."""
        features, forward_returns = strategy._create_features(sample_data)

        assert features is not None
        assert isinstance(features, pd.DataFrame)
        assert len(features) == len(sample_data)
        assert len(forward_returns) == len(sample_data)

    def test_predict_rule_based(self, strategy, sample_data):
        """Test rule-based prediction."""
        features, _ = strategy._create_features(sample_data)
        
        signals, confidences = strategy._predict_rule_based(features)

        assert isinstance(signals, np.ndarray)
        assert isinstance(confidences, np.ndarray)
        assert len(signals) == len(features)
        assert len(confidences) == len(features)

    def test_get_feature_importance_no_model(self, strategy):
        """Test feature importance returns None when model not trained."""
        importance = strategy.get_feature_importance()

        assert importance is None

    def test_apply_position_logic(self, strategy):
        """Test position logic application."""
        signals = np.array([1, 0, 0, 0, -1, 0, 0, 1, 0, 0])
        confidences = np.array([0.8, 0.5, 0.4, 0.3, 0.9, 0.8, 0.7, 0.9, 0.6, 0.5])

        result = strategy._apply_position_logic(signals, confidences)

        assert isinstance(result, np.ndarray)
        assert set(result).issubset({-1, 0, 1})

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "MomentumMLStrategy" in repr_str
        assert "feature_lookback" in repr_str


class TestSimpleMomentumStrategy:
    """Tests for SimpleMomentumStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create Simple Momentum strategy instance."""
        return SimpleMomentumStrategy()

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        prices = 100 + np.cumsum(np.random.randn(100) * 2)

        return pd.DataFrame({
            "close": prices,
        }, index=dates)

    def test_init(self, strategy):
        """Test initialization."""
        assert strategy.rsi_period == 14
        assert strategy.rsi_oversold == 30.0
        assert strategy.rsi_overbought == 70.0
        assert strategy.momentum_period == 10

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert strategy.required_columns == ["close"]

    def test_min_periods(self, strategy):
        """Test minimum periods calculation."""
        # min_periods = max(rsi_period, momentum_period) + 5 = max(14, 10) + 5 = 19
        assert strategy.min_periods == 19

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

    def test_get_indicator_rsi(self, strategy, sample_data):
        """Test getting RSI indicator."""
        strategy.generate_signals(sample_data)

        rsi = strategy.get_indicator("rsi")

        assert rsi is not None
        assert len(rsi) == len(sample_data)

    def test_get_indicator_momentum(self, strategy, sample_data):
        """Test getting momentum indicator."""
        strategy.generate_signals(sample_data)

        momentum = strategy.get_indicator("momentum")

        assert momentum is not None
        assert len(momentum) == len(sample_data)


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestStrategyEdgeCases:
    """Edge case tests for ML strategies."""

    def test_constant_price_data(self):
        """Test strategy with constant price data."""
        data = pd.DataFrame({
            "close": [100.0] * 100,
            "high": [101.0] * 100,
            "low": [99.0] * 100,
        })
        
        # Test TrendClassifier
        trend_strategy = TrendClassifierStrategy()
        trend_signals = trend_strategy.generate_signals(data)
        assert set(trend_signals).issubset({-1, 0, 1})
        
        # Test MomentumML
        momentum_strategy = MomentumMLStrategy(MomentumMLConfig(use_ml_model=False))
        momentum_signals = momentum_strategy.generate_signals(data)
        assert set(momentum_signals).issubset({-1, 0, 1})

    def test_high_volatility_data(self):
        """Test strategy with high volatility data."""
        np.random.seed(42)
        prices = [100]
        for _ in range(99):
            prices.append(prices[-1] + np.random.randn() * 10)
        
        data = pd.DataFrame({
            "close": prices,
            "high": [p + abs(np.random.rand() * 5) for p in prices],
            "low": [p - abs(np.random.rand() * 5) for p in prices],
        })
        
        # Test TrendClassifier
        trend_strategy = TrendClassifierStrategy()
        trend_signals = trend_strategy.generate_signals(data)
        assert set(trend_signals).issubset({-1, 0, 1})

    def test_uptrend_data(self):
        """Test strategy with strongly upward trending data."""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5 + 1)
        
        data = pd.DataFrame({
            "close": prices,
            "high": prices + abs(np.random.randn(100)) * 2,
            "low": prices - abs(np.random.randn(100)) * 2,
        })
        
        strategy = TrendClassifierStrategy()
        signals = strategy.generate_signals(data)
        
        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})

    def test_downtrend_data(self):
        """Test strategy with strongly downward trending data."""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5 - 1)
        
        data = pd.DataFrame({
            "close": prices,
            "high": prices + abs(np.random.randn(100)) * 2,
            "low": prices - abs(np.random.randn(100)) * 2,
        })
        
        strategy = TrendClassifierStrategy()
        signals = strategy.generate_signals(data)
        
        assert isinstance(signals, np.ndarray)
        assert set(signals).issubset({-1, 0, 1})
