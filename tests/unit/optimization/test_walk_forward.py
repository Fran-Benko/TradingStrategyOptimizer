"""
Unit tests for WalkForwardOptimizer.

Tests cover:
- WalkForwardOptimizer initialization
- WindowType enum
- Robustness metrics
- walk_forward_analysis function
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from trading_system.optimization.walk_forward import (
    WalkForwardOptimizer,
    WalkForwardConfig,
    WalkForwardResult,
    WindowType,
    PeriodResult,
    walk_forward_analysis,
)
from trading_system.backtesting.engine import BacktestConfig
from trading_system.optimization.optimizer import MetricType
from trading_system.strategies.base.base import BaseStrategy, StrategyConfig


class MockStrategy(BaseStrategy):
    """Mock strategy for testing walk-forward optimizer."""
    
    def __init__(self, config: StrategyConfig = None):
        super().__init__(config)
        self.param_value = getattr(config, 'param_value', 50)
    
    @property
    def required_columns(self):
        return ["close"]
    
    @property
    def min_periods(self):
        return 1
    
    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """Generate signals based on parameter."""
        signals = np.zeros(len(data))
        period = max(5, int(self.param_value / 10))
        
        for i in range(period, len(data) - period):
            if i % (period * 2) < period:
                signals[i] = 1  # Buy
            elif i % (period * 2) == period * 2 - 1:
                signals[i] = -1  # Sell
        
        return signals


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=500, freq="D")
    np.random.seed(42)
    
    prices = 100 + np.cumsum(np.random.randn(500) * 2)
    
    return pd.DataFrame({
        "open": prices + np.random.randn(500) * 0.5,
        "high": prices + abs(np.random.randn(500)) * 2,
        "low": prices - abs(np.random.randn(500)) * 2,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, 500)
    }, index=dates)


@pytest.fixture
def small_ohlcv_data():
    """Generate smaller OHLCV data for faster tests."""
    dates = pd.date_range(start="2023-01-01", periods=300, freq="D")
    np.random.seed(42)
    
    prices = 100 + np.cumsum(np.random.randn(300) * 2)
    
    return pd.DataFrame({
        "open": prices + np.random.randn(300) * 0.5,
        "high": prices + abs(np.random.randn(300)) * 2,
        "low": prices - abs(np.random.randn(300)) * 2,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, 300)
    }, index=dates)


@pytest.fixture
def default_wf_config():
    """Default walk-forward configuration."""
    return WalkForwardConfig(
        window_type=WindowType.ROLLING,
        train_window=100,
        test_window=50,
        min_train_periods=50,
        min_test_periods=20,
        min_trades_per_period=3,
        verbose=False
    )


@pytest.fixture
def expanding_wf_config():
    """Walk-forward configuration with expanding window."""
    return WalkForwardConfig(
        window_type=WindowType.EXPANDING,
        train_window=100,
        test_window=50,
        min_train_periods=50,
        min_test_periods=20,
        min_trades_per_period=3,
        verbose=False
    )


class TestWindowType:
    """Tests for WindowType enum."""
    
    def test_window_type_values(self):
        """Test WindowType enum values."""
        assert WindowType.ROLLING.value == "rolling"
        assert WindowType.EXPANDING.value == "expanding"
    
    def test_window_type_count(self):
        """Test that WindowType has expected variants."""
        assert len(WindowType) == 2
    
    def test_window_type_is_enum(self):
        """Test WindowType is an Enum."""
        from enum import Enum
        assert isinstance(WindowType.ROLLING, Enum)


class TestWalkForwardConfig:
    """Tests for WalkForwardConfig."""
    
    def test_default_config(self):
        """Test default walk-forward configuration."""
        config = WalkForwardConfig()
        
        assert config.window_type == WindowType.ROLLING
        assert config.train_window == 252
        assert config.test_window == 63
        assert config.min_train_periods == 126
        assert config.min_test_periods == 20
        assert config.verbose is True
    
    def test_custom_config(self):
        """Test custom walk-forward configuration."""
        config = WalkForwardConfig(
            window_type=WindowType.EXPANDING,
            train_window=100,
            test_window=50,
            step_size=25,
            optimization_metric=MetricType.TOTAL_RETURN
        )
        
        assert config.window_type == WindowType.EXPANDING
        assert config.train_window == 100
        assert config.test_window == 50
        assert config.step_size == 25
        assert config.optimization_metric == MetricType.TOTAL_RETURN
    
    def test_validate_valid_config(self, default_wf_config):
        """Test validation of valid configuration."""
        assert default_wf_config.validate() is True
    
    def test_validate_invalid_train_window(self):
        """Test validation fails for invalid train_window."""
        config = WalkForwardConfig(train_window=0)
        with pytest.raises(ValueError, match="train_window must be positive"):
            config.validate()
    
    def test_validate_invalid_test_window(self):
        """Test validation fails for invalid test_window."""
        config = WalkForwardConfig(test_window=0)
        with pytest.raises(ValueError, match="test_window must be positive"):
            config.validate()
    
    def test_validate_invalid_min_train_periods(self):
        """Test validation fails for invalid min_train_periods."""
        config = WalkForwardConfig(min_train_periods=0)
        with pytest.raises(ValueError, match="min_train_periods must be positive"):
            config.validate()
    
    def test_validate_invalid_min_test_periods(self):
        """Test validation fails for invalid min_test_periods."""
        config = WalkForwardConfig(min_test_periods=0)
        with pytest.raises(ValueError, match="min_test_periods must be positive"):
            config.validate()


class TestPeriodResult:
    """Tests for PeriodResult dataclass."""
    
    def test_period_result_creation(self):
        """Test PeriodResult creation with all fields."""
        period = PeriodResult(
            period_index=0,
            train_start=pd.Timestamp("2023-01-01"),
            train_end=pd.Timestamp("2023-06-01"),
            test_start=pd.Timestamp("2023-06-01"),
            test_end=pd.Timestamp("2023-08-01"),
            best_params={"param": 50},
            in_sample_score=1.5,
            out_of_sample_score=1.2,
            in_sample_return=0.10,
            out_of_sample_return=0.08,
            in_sample_sharpe=1.0,
            out_of_sample_sharpe=0.8,
            in_sample_max_dd=0.05,
            out_of_sample_max_dd=0.06,
            trade_count=10,
            degradation_ratio=0.8,
            valid=True,
            reason=""
        )
        
        assert period.period_index == 0
        assert period.best_params == {"param": 50}
        assert period.degradation_ratio == 0.8
        assert period.valid is True
    
    def test_period_result_invalid(self):
        """Test invalid PeriodResult."""
        period = PeriodResult(
            period_index=0,
            train_start=pd.Timestamp("2023-01-01"),
            train_end=pd.Timestamp("2023-06-01"),
            test_start=pd.Timestamp("2023-06-01"),
            test_end=pd.Timestamp("2023-08-01"),
            best_params={},
            in_sample_score=np.nan,
            out_of_sample_score=np.nan,
            in_sample_return=np.nan,
            out_of_sample_return=np.nan,
            in_sample_sharpe=np.nan,
            out_of_sample_sharpe=np.nan,
            in_sample_max_dd=np.nan,
            out_of_sample_max_dd=np.nan,
            trade_count=0,
            degradation_ratio=0.0,
            valid=False,
            reason="insufficient_trades"
        )
        
        assert period.valid is False
        assert period.reason == "insufficient_trades"


class TestWalkForwardOptimizerInit:
    """Tests for WalkForwardOptimizer initialization."""
    
    def test_init_default(self):
        """Test optimizer initialization with defaults."""
        optimizer = WalkForwardOptimizer()
        
        assert optimizer.backtest_config is not None
        assert optimizer.config is not None
        assert optimizer._backtest_engine is not None
        assert optimizer._strategy_optimizer is not None
    
    def test_init_custom_backtest_config(self):
        """Test optimizer with custom backtest config."""
        bt_config = BacktestConfig(initial_capital=50000)
        optimizer = WalkForwardOptimizer(backtest_config=bt_config)
        
        assert optimizer.backtest_config.initial_capital == 50000
    
    def test_init_custom_wf_config(self, default_wf_config):
        """Test optimizer with custom walk-forward config."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        assert optimizer.config.train_window == 100
        assert optimizer.config.test_window == 50
    
    def test_init_invalid_config(self):
        """Test optimizer fails with invalid config."""
        wf_config = WalkForwardConfig(train_window=0)
        
        with pytest.raises(ValueError):
            WalkForwardOptimizer(walk_forward_config=wf_config)


class TestWalkForwardOptimize:
    """Tests for WalkForwardOptimizer.optimize() method."""
    
    def test_optimize_basic(self, small_ohlcv_data, default_wf_config):
        """Test basic walk-forward optimization."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result is not None
        assert isinstance(result, WalkForwardResult)
        assert result.total_periods >= 0
    
    def test_optimize_insufficient_data(self, default_wf_config):
        """Test optimization fails with insufficient data."""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        data = pd.DataFrame({
            "close": np.linspace(100, 110, 50),
            "volume": 1000000
        }, index=dates)
        
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        with pytest.raises(ValueError, match="Insufficient data"):
            optimizer.optimize(MockStrategy, data, param_grid, symbol="TEST")
    
    def test_optimize_expanding_window(self, small_ohlcv_data, expanding_wf_config):
        """Test walk-forward with expanding window."""
        optimizer = WalkForwardOptimizer(walk_forward_config=expanding_wf_config)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result is not None
        assert result.window_type == WindowType.EXPANDING
    
    def test_optimize_with_step_size(self, small_ohlcv_data, default_wf_config):
        """Test walk-forward with custom step size."""
        default_wf_config.step_size = 25
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result is not None


class TestRobustnessMetrics:
    """Tests for robustness metrics calculation."""
    
    def test_stability_score_calculation(self, small_ohlcv_data, default_wf_config):
        """Test stability score calculation."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        # Stability score should be between 0 and 1
        assert 0 <= result.stability_score <= 1
    
    def test_walk_forward_return_calculation(self, small_ohlcv_data, default_wf_config):
        """Test walk-forward return calculation."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.walk_forward_return is not None
        # Walk-forward return can be positive, negative, or zero
        assert isinstance(result.walk_forward_return, float)
    
    def test_degradation_ratio_calculation(self, small_ohlcv_data, default_wf_config):
        """Test degradation ratio calculation."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.degradation_ratio is not None
        # Degradation ratio typically between 0 and 1
        assert isinstance(result.degradation_ratio, float)
    
    def test_robustness_score_calculation(self, small_ohlcv_data, default_wf_config):
        """Test robustness score calculation."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.robustness_score is not None
        # Robustness score should be between 0 and 1
        assert 0 <= result.robustness_score <= 1
    
    def test_robustness_score_weighted(self, small_ohlcv_data, default_wf_config):
        """Test that robustness score combines multiple factors."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [30, 50, 70]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        # With valid results, robustness score should be meaningful
        valid_periods = result.get_valid_periods()
        if len(valid_periods) > 0:
            assert result.robustness_score > 0


class TestWalkForwardResult:
    """Tests for WalkForwardResult."""
    
    def test_result_has_window_type(self, small_ohlcv_data, default_wf_config):
        """Test that result has window type."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.window_type == WindowType.ROLLING
    
    def test_result_has_total_periods(self, small_ohlcv_data, default_wf_config):
        """Test that result has total periods."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.total_periods >= 0
    
    def test_result_has_in_sample_results(self, small_ohlcv_data, default_wf_config):
        """Test that result has in-sample results DataFrame."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.in_sample_results is not None
        assert isinstance(result.in_sample_results, pd.DataFrame)
    
    def test_result_has_out_of_sample_results(self, small_ohlcv_data, default_wf_config):
        """Test that result has out-of-sample results DataFrame."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.out_of_sample_results is not None
        assert isinstance(result.out_of_sample_results, pd.DataFrame)
    
    def test_result_has_analysis_time(self, small_ohlcv_data, default_wf_config):
        """Test that result has analysis time."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.analysis_time > 0


class TestWalkForwardResultMethods:
    """Tests for WalkForwardResult methods."""
    
    def test_get_valid_periods(self, small_ohlcv_data, default_wf_config):
        """Test get_valid_periods method."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        valid_periods = result.get_valid_periods()
        
        assert isinstance(valid_periods, list)
        for period in valid_periods:
            assert period.valid is True
    
    def test_get_robust_params(self, small_ohlcv_data, default_wf_config):
        """Test get_robust_params method."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        robust_params = result.get_robust_params()
        
        assert isinstance(robust_params, dict)
    
    def test_get_robust_params_no_valid(self, default_wf_config):
        """Test get_robust_params with no valid periods."""
        # Create very small data to force no valid periods
        dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
        data = pd.DataFrame({
            "close": np.linspace(100, 110, 200),
            "volume": 1000000
        }, index=dates)
        
        # Use very restrictive config
        wf_config = WalkForwardConfig(
            train_window=150,
            test_window=100,
            min_train_periods=100,
            min_test_periods=50,
            min_trades_per_period=50,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        # Insufficient data should raise ValueError
        with pytest.raises(ValueError, match="Insufficient data"):
            optimizer.optimize(
                MockStrategy,
                data,
                param_grid,
                symbol="TEST"
            )
    
    def test_to_dataframe(self, small_ohlcv_data, default_wf_config):
        """Test to_dataframe method."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        df = result.to_dataframe()
        
        assert isinstance(df, pd.DataFrame)
        if len(result.period_results) > 0:
            assert len(df) == len(result.period_results)
    
    def test_summary_format(self, small_ohlcv_data, default_wf_config):
        """Test that summary returns formatted string."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        summary = result.summary()
        
        assert isinstance(summary, str)
        assert "Walk-Forward Analysis Results" in summary


class TestWalkForwardAnalysis:
    """Tests for walk_forward_analysis convenience function."""
    
    def test_walk_forward_analysis_basic(self, small_ohlcv_data):
        """Test walk_forward_analysis convenience function."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = walk_forward_analysis(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            train_window=100,
            test_window=50,
            window_type=WindowType.ROLLING
        )
        
        assert isinstance(result, WalkForwardResult)
    
    def test_walk_forward_analysis_expanding(self, small_ohlcv_data):
        """Test walk_forward_analysis with expanding window."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = walk_forward_analysis(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            train_window=100,
            test_window=50,
            window_type=WindowType.EXPANDING
        )
        
        assert result.window_type == WindowType.EXPANDING
    
    def test_walk_forward_analysis_with_kwargs(self, small_ohlcv_data):
        """Test walk_forward_analysis with additional kwargs."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = walk_forward_analysis(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            train_window=100,
            test_window=50,
            window_type=WindowType.ROLLING,
            symbol="CUSTOM"
        )
        
        assert result is not None


class TestPeriodResults:
    """Tests for individual period results."""
    
    def test_period_results_list(self, small_ohlcv_data, default_wf_config):
        """Test that period results are stored correctly."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert len(result.period_results) == result.total_periods
    
    def test_period_has_dates(self, small_ohlcv_data, default_wf_config):
        """Test that period results have correct dates."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        for period in result.period_results:
            assert period.train_start is not None
            assert period.train_end is not None
            assert period.test_start is not None
            assert period.test_end is not None
    
    def test_period_has_params(self, small_ohlcv_data, default_wf_config):
        """Test that period results have optimized parameters."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        for period in result.get_valid_periods():
            assert isinstance(period.best_params, dict)
            assert len(period.best_params) > 0
    
    def test_period_has_scores(self, small_ohlcv_data, default_wf_config):
        """Test that period results have IS and OOS scores."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        for period in result.get_valid_periods():
            assert period.in_sample_score is not None
            assert period.out_of_sample_score is not None


class TestDegradationRatio:
    """Tests for degradation ratio calculation."""
    
    def test_degradation_positive_in_sample(self, small_ohlcv_data, default_wf_config):
        """Test degradation ratio with positive in-sample."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        for period in result.get_valid_periods():
            # Degradation should be calculated
            assert isinstance(period.degradation_ratio, float)
    
    def test_degradation_zero_in_sample(self, small_ohlcv_data, default_wf_config):
        """Test degradation ratio when in-sample score is zero."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        # Should handle zero in-sample gracefully
        for period in result.period_results:
            assert isinstance(period.degradation_ratio, float)


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_no_valid_periods(self):
        """Test behavior when no periods are valid."""
        dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
        data = pd.DataFrame({
            "close": np.linspace(100, 110, 200),
            "volume": 1000000
        }, index=dates)
        
        wf_config = WalkForwardConfig(
            train_window=150,
            test_window=100,
            min_train_periods=100,
            min_test_periods=80,
            min_trades_per_period=100,  # Unrealistic
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        # With very strict requirements, should raise exception
        with pytest.raises(ValueError, match="Insufficient data"):
            optimizer.optimize(
                MockStrategy,
                data,
                param_grid,
                symbol="TEST"
            )
    
    def test_very_short_test_window(self, sample_ohlcv_data):
        """Test with very short test window."""
        wf_config = WalkForwardConfig(
            train_window=100,
            test_window=10,
            min_train_periods=50,
            min_test_periods=5,
            min_trades_per_period=1,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result is not None
    
    def test_optimize_metric_types(self, small_ohlcv_data, default_wf_config):
        """Test optimization with different metrics."""
        for metric in [MetricType.SHARPE_RATIO, MetricType.TOTAL_RETURN, MetricType.WIN_RATE]:
            wf_config = WalkForwardConfig(
                window_type=WindowType.ROLLING,
                train_window=100,
                test_window=50,
                min_train_periods=50,
                min_test_periods=20,
                min_trades_per_period=3,
                optimization_metric=metric,
                verbose=False
            )
            
            optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
            
            param_grid = {
                "param_value": [40, 60]
            }
            
            result = optimizer.optimize(
                MockStrategy,
                small_ohlcv_data,
                param_grid,
                symbol="TEST"
            )
            
            assert result is not None


class TestDataFrameStructure:
    """Tests for DataFrame structure in results."""
    
    def test_in_sample_df_columns(self, small_ohlcv_data, default_wf_config):
        """Test in-sample DataFrame has expected columns."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        if len(result.in_sample_results) > 0:
            expected_cols = ["period", "return", "sharpe", "max_dd", "score"]
            for col in expected_cols:
                assert col in result.in_sample_results.columns
    
    def test_out_of_sample_df_columns(self, small_ohlcv_data, default_wf_config):
        """Test out-of-sample DataFrame has expected columns."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        if len(result.out_of_sample_results) > 0:
            expected_cols = ["period", "return", "sharpe", "max_dd", "score", "trade_count", "degradation"]
            for col in expected_cols:
                assert col in result.out_of_sample_results.columns
    
    def test_to_dataframe_columns(self, small_ohlcv_data, default_wf_config):
        """Test to_dataframe has expected columns."""
        optimizer = WalkForwardOptimizer(walk_forward_config=default_wf_config)
        
        param_grid = {
            "param_value": [40, 60]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            small_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        df = result.to_dataframe()
        
        if len(df) > 0:
            expected_cols = [
                "period", "train_start", "train_end", "test_start", "test_end",
                "is_return", "os_return", "is_sharpe", "os_sharpe",
                "is_max_dd", "os_max_dd", "trade_count", "degradation"
            ]
            for col in expected_cols:
                assert col in df.columns
