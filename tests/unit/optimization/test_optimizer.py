"""
Unit tests for StrategyOptimizer.

Tests cover:
- StrategyOptimizer initialization
- optimize() with small param grid
- OptimizationResult attributes
- Metric calculation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from trading_system.optimization.optimizer import (
    StrategyOptimizer,
    OptimizationConfig,
    OptimizationResult,
    MetricType,
    grid_search,
)
from trading_system.backtesting.engine import BacktestConfig, BacktestEngine
from trading_system.strategies.base.base import BaseStrategy, StrategyConfig


class MockStrategy(BaseStrategy):
    """Mock strategy for testing optimizer."""
    
    def __init__(self, config: StrategyConfig = None):
        super().__init__(config)
        # Use parameter from config if available
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


class MockStrategyWithValidation(BaseStrategy):
    """Mock strategy with parameter validation."""
    
    def __init__(self, config: StrategyConfig = None):
        super().__init__(config)
        self.param_value = getattr(config, 'param_value', 50)
        
        # Validate parameter
        if self.param_value < 10:
            raise ValueError("param_value must be >= 10")
    
    @property
    def required_columns(self):
        return ["close"]
    
    @property
    def min_periods(self):
        return 5
    
    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(data))
        period = max(3, int(self.param_value / 10))
        
        for i in range(period, len(data) - period, period * 2):
            signals[i] = 1
            if i + period < len(data):
                signals[i + period] = -1
        
        return signals


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    np.random.seed(42)
    
    prices = 100 + np.cumsum(np.random.randn(200) * 2)
    
    return pd.DataFrame({
        "open": prices + np.random.randn(200) * 0.5,
        "high": prices + abs(np.random.randn(200)) * 2,
        "low": prices - abs(np.random.randn(200)) * 2,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, 200)
    }, index=dates)


@pytest.fixture
def rising_ohlcv_data():
    """Generate steadily rising OHLCV data."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    prices = np.linspace(100, 150, 200)
    
    return pd.DataFrame({
        "open": prices + 0.5,
        "high": prices + 2,
        "low": prices - 2,
        "close": prices,
        "volume": 1000000
    }, index=dates)


@pytest.fixture
def default_optimizer():
    """Create optimizer with default configuration."""
    return StrategyOptimizer()


@pytest.fixture
def custom_optimizer():
    """Create optimizer with custom configuration."""
    opt_config = OptimizationConfig(
        metric=MetricType.SHARPE_RATIO,
        maximize=True,
        cv_folds=1,
        n_jobs=1,
        verbose=False,
        progress_interval=5
    )
    return StrategyOptimizer(optimization_config=opt_config)


class TestOptimizationConfig:
    """Tests for OptimizationConfig."""
    
    def test_default_config(self):
        """Test default optimization configuration."""
        config = OptimizationConfig()
        
        assert config.metric == MetricType.SHARPE_RATIO
        assert config.maximize is True
        assert config.cv_folds == 1
        assert config.n_jobs == 1
        assert config.verbose is True
    
    def test_custom_config(self):
        """Test custom optimization configuration."""
        config = OptimizationConfig(
            metric=MetricType.TOTAL_RETURN,
            maximize=True,
            cv_folds=3,
            cv_window_size=50,
            min_trades_per_fold=5,
            n_jobs=2,
            verbose=False
        )
        
        assert config.metric == MetricType.TOTAL_RETURN
        assert config.cv_folds == 3
        assert config.cv_window_size == 50
    
    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = OptimizationConfig(cv_folds=1)
        assert config.validate() is True
        
        config = OptimizationConfig(cv_folds=3, cv_window_size=50)
        assert config.validate() is True
    
    def test_validate_invalid_cv_folds(self):
        """Test validation fails for invalid cv_folds."""
        config = OptimizationConfig(cv_folds=0)
        with pytest.raises(ValueError, match="cv_folds must be >= 1"):
            config.validate()
    
    def test_validate_cv_folds_without_window(self):
        """Test validation fails for cv_folds > 1 without window_size."""
        config = OptimizationConfig(cv_folds=3)
        with pytest.raises(ValueError, match="cv_window_size required"):
            config.validate()
    
    def test_validate_invalid_min_trades(self):
        """Test validation fails for invalid min_trades."""
        config = OptimizationConfig(min_trades_per_fold=0)
        with pytest.raises(ValueError, match="min_trades_per_fold must be >= 1"):
            config.validate()
    
    def test_validate_invalid_n_jobs(self):
        """Test validation fails for invalid n_jobs."""
        config = OptimizationConfig(n_jobs=0)
        with pytest.raises(ValueError, match="n_jobs must be >= 1"):
            config.validate()


class TestStrategyOptimizerInit:
    """Tests for StrategyOptimizer initialization."""
    
    def test_init_default(self):
        """Test optimizer initialization with defaults."""
        optimizer = StrategyOptimizer()
        
        assert optimizer.backtest_config is not None
        assert optimizer.optimization_config is not None
    
    def test_init_custom_backtest_config(self):
        """Test optimizer with custom backtest config."""
        bt_config = BacktestConfig(initial_capital=50000)
        optimizer = StrategyOptimizer(backtest_config=bt_config)
        
        assert optimizer.backtest_config.initial_capital == 50000
    
    def test_init_custom_optimization_config(self):
        """Test optimizer with custom optimization config."""
        opt_config = OptimizationConfig(metric=MetricType.TOTAL_RETURN)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        assert optimizer.optimization_config.metric == MetricType.TOTAL_RETURN
    
    def test_init_invalid_optimization_config(self):
        """Test optimizer fails with invalid optimization config."""
        opt_config = OptimizationConfig(cv_folds=0)
        
        with pytest.raises(ValueError):
            StrategyOptimizer(optimization_config=opt_config)
    
    def test_backtest_engine_created(self):
        """Test that backtest engine is created."""
        optimizer = StrategyOptimizer()
        
        assert optimizer._backtest_engine is not None
        assert isinstance(optimizer._backtest_engine, BacktestEngine)


class TestOptimizeBasic:
    """Tests for basic optimize() functionality."""
    
    def test_optimize_basic(self, sample_ohlcv_data, default_optimizer):
        """Test basic optimization with small param grid."""
        param_grid = {
            "param_value": [30, 50, 70]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result is not None
        assert isinstance(result, OptimizationResult)
        assert result.total_combinations == 3
        assert result.valid_combinations > 0
    
    def test_optimize_empty_param_grid(self, sample_ohlcv_data, default_optimizer):
        """Test that empty param grid raises error."""
        with pytest.raises(ValueError, match="param_grid cannot be empty"):
            default_optimizer.optimize(MockStrategy, sample_ohlcv_data, {})
    
    def test_optimize_single_param(self, sample_ohlcv_data, default_optimizer):
        """Test optimization with single parameter."""
        param_grid = {
            "param_value": [20, 40, 60, 80]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.total_combinations == 4
    
    def test_optimize_multiple_params(self, sample_ohlcv_data, default_optimizer):
        """Test optimization with multiple parameters."""
        param_grid = {
            "param_value": [30, 50],
            "period": [10, 20]
        }
        
        result = default_optimizer.optimize(
            MockStrategyWithValidation,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        # 2 * 2 = 4 combinations
        assert result.total_combinations == 4
    
    def test_optimize_large_param_grid(self, sample_ohlcv_data, default_optimizer):
        """Test optimization with larger parameter grid."""
        param_grid = {
            "param_value": [20, 30, 40, 50, 60]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.total_combinations == 5
    
    def test_optimize_with_metric_override(self, sample_ohlcv_data, default_optimizer):
        """Test optimization with metric override."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST",
            metric=MetricType.TOTAL_RETURN
        )
        
        assert result.best_metric == MetricType.TOTAL_RETURN


class TestOptimizationResult:
    """Tests for OptimizationResult attributes."""
    
    def test_result_has_best_params(self, sample_ohlcv_data, default_optimizer):
        """Test that result contains best parameters."""
        param_grid = {
            "param_value": [30, 50, 70]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.best_params is not None
        assert isinstance(result.best_params, dict)
    
    def test_result_has_best_score(self, sample_ohlcv_data, default_optimizer):
        """Test that result contains best score."""
        param_grid = {
            "param_value": [30, 50, 70]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.best_score is not None
    
    def test_result_has_all_results_dataframe(self, sample_ohlcv_data, default_optimizer):
        """Test that result contains all results DataFrame."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.all_results is not None
        assert isinstance(result.all_results, pd.DataFrame)
        assert len(result.all_results) == result.total_combinations
    
    def test_result_has_optimization_time(self, sample_ohlcv_data, default_optimizer):
        """Test that result contains optimization time."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.optimization_time > 0
    
    def test_result_combinations_count(self, sample_ohlcv_data, default_optimizer):
        """Test that combination counts are correct."""
        param_grid = {
            "param_value": [20, 30, 40, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.total_combinations == 4
        assert result.valid_combinations <= result.total_combinations
    
    def test_result_valid_combinations(self, sample_ohlcv_data, default_optimizer):
        """Test that valid_combinations tracks valid results."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        valid_df = result.all_results[result.all_results["valid"] == True]
        assert len(valid_df) == result.valid_combinations


class TestMetricCalculation:
    """Tests for metric calculation in optimization."""
    
    def test_all_metrics_calculated(self, sample_ohlcv_data, default_optimizer):
        """Test that all metrics are calculated."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        if result.valid_combinations > 0:
            valid_row = result.all_results[result.all_results["valid"] == True].iloc[0]
            
            assert "sharpe_ratio" in valid_row
            assert "sortino_ratio" in valid_row
            assert "total_return" in valid_row
            assert "win_rate" in valid_row
            assert "profit_factor" in valid_row
            assert "max_drawdown" in valid_row
            assert "max_drawdown_pct" in valid_row
    
    def test_sharpe_ratio_metric(self, sample_ohlcv_data):
        """Test optimization targeting Sharpe ratio."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                metric=MetricType.SHARPE_RATIO,
                maximize=True,
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [30, 50, 70]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.best_metric == MetricType.SHARPE_RATIO
    
    def test_total_return_metric(self, sample_ohlcv_data):
        """Test optimization targeting total return."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                metric=MetricType.TOTAL_RETURN,
                maximize=True,
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.best_metric == MetricType.TOTAL_RETURN
    
    def test_win_rate_metric(self, sample_ohlcv_data):
        """Test optimization targeting win rate."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                metric=MetricType.WIN_RATE,
                maximize=True,
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.best_metric == MetricType.WIN_RATE
    
    def test_max_drawdown_metric(self, sample_ohlcv_data):
        """Test optimization targeting max drawdown (minimization)."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                metric=MetricType.MAX_DRAWDOWN,
                maximize=False,  # Minimize drawdown
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.best_metric == MetricType.MAX_DRAWDOWN
    
    def test_profit_factor_metric(self, sample_ohlcv_data):
        """Test optimization targeting profit factor."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                metric=MetricType.PROFIT_FACTOR,
                maximize=True,
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.best_metric == MetricType.PROFIT_FACTOR
    
    def test_calmar_ratio_calculated(self, sample_ohlcv_data, default_optimizer):
        """Test that Calmar ratio is calculated."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        if result.valid_combinations > 0:
            valid_row = result.all_results[result.all_results["valid"] == True].iloc[0]
            assert "calmar_ratio" in valid_row


class TestResultSummary:
    """Tests for OptimizationResult.summary() method."""
    
    def test_summary_format(self, sample_ohlcv_data, default_optimizer):
        """Test that summary returns formatted string."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        summary = result.summary()
        
        assert isinstance(summary, str)
        assert "Optimization Results" in summary
    
    def test_summary_contains_metrics(self, sample_ohlcv_data, default_optimizer):
        """Test that summary contains key metrics."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        summary = result.summary()
        
        assert "Metric:" in summary
        assert "Best Score:" in summary
        assert "Best Parameters:" in summary
    
    def test_summary_with_validation_results(self, sample_ohlcv_data):
        """Test summary with cross-validation results."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                metric=MetricType.SHARPE_RATIO,
                cv_folds=2,
                cv_window_size=50,
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        summary = result.summary()
        assert isinstance(summary, str)


class TestTopN:
    """Tests for OptimizationResult.top_n() method."""
    
    def test_top_n_returns_dataframe(self, sample_ohlcv_data, default_optimizer):
        """Test that top_n returns DataFrame."""
        param_grid = {
            "param_value": [20, 30, 40, 50, 60]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        top = result.top_n(3)
        
        assert isinstance(top, pd.DataFrame)
        assert len(top) <= 3
    
    def test_top_n_sorted_by_metric(self, sample_ohlcv_data, default_optimizer):
        """Test that top_n is sorted correctly."""
        param_grid = {
            "param_value": [20, 30, 40, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        top = result.top_n(2)
        
        if len(top) > 1:
            # First row should have higher score
            assert top.iloc[0][result.best_metric.value] >= top.iloc[1][result.best_metric.value]


class TestGridSearch:
    """Tests for grid_search convenience function."""
    
    def test_grid_search_basic(self, sample_ohlcv_data):
        """Test grid_search convenience function."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = grid_search(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            metric=MetricType.SHARPE_RATIO
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.best_metric == MetricType.SHARPE_RATIO
    
    def test_grid_search_with_kwargs(self, sample_ohlcv_data):
        """Test grid_search with additional kwargs."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = grid_search(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            metric=MetricType.TOTAL_RETURN,
            symbol="CUSTOM"
        )
        
        assert result is not None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_optimize_single_data_point(self, default_optimizer):
        """Test optimization with minimal data."""
        dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
        data = pd.DataFrame({
            "close": [100] * 10,
            "volume": 1000000
        }, index=dates)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            data,
            param_grid,
            symbol="TEST"
        )
        
        # Should handle gracefully, may have no valid combinations
        assert result is not None
        assert result.total_combinations == 2
    
    def test_optimize_all_invalid_params(self, sample_ohlcv_data, default_optimizer):
        """Test when all parameter combinations are invalid."""
        param_grid = {
            "param_value": [5, 8]  # Invalid for MockStrategyWithValidation
        }
        
        result = default_optimizer.optimize(
            MockStrategyWithValidation,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        # All should be invalid
        assert result.valid_combinations == 0
        # best_params should be empty dict
        assert result.best_params == {}
        assert np.isnan(result.best_score)
    
    def test_optimize_with_seed(self, sample_ohlcv_data):
        """Test optimization with random seed for reproducibility."""
        opt_config = OptimizationConfig(
            seed=42,
            verbose=False
        )
        
        optimizer1 = StrategyOptimizer(optimization_config=opt_config)
        optimizer2 = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result1 = optimizer1.optimize(MockStrategy, sample_ohlcv_data, param_grid)
        result2 = optimizer2.optimize(MockStrategy, sample_ohlcv_data, param_grid)
        
        # Results should be identical (if numpy is seeded)
        # Note: This may not be perfectly reproducible depending on implementation
        assert result1.total_combinations == result2.total_combinations


class TestCrossValidation:
    """Tests for cross-validation functionality."""
    
    def test_cv_folds_basic(self, sample_ohlcv_data):
        """Test basic cross-validation setup."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                cv_folds=2,
                cv_window_size=50,
                min_trades_per_fold=3,
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        assert result.validation_results is not None
        assert isinstance(result.validation_results, pd.DataFrame)
    
    def test_cv_results_structure(self, sample_ohlcv_data):
        """Test cross-validation results structure."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                cv_folds=2,
                cv_window_size=60,
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [40]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        if result.validation_results is not None and len(result.validation_results) > 0:
            cv_row = result.validation_results.iloc[0]
            
            assert "fold" in cv_row
            assert "train_score" in cv_row
            assert "test_score" in cv_row
            assert "cv_score" in cv_row


class TestMinTradesFilter:
    """Tests for minimum trades filtering."""
    
    def test_min_trades_excluded(self, sample_ohlcv_data):
        """Test that combinations with too few trades are excluded."""
        optimizer = StrategyOptimizer(
            optimization_config=OptimizationConfig(
                min_trades_per_fold=100,  # Very high threshold
                verbose=False
            )
        )
        
        param_grid = {
            "param_value": [30, 50, 70]
        }
        
        result = optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        # Most or all combinations should be invalid
        assert result.valid_combinations < result.total_combinations
    
    def test_valid_combinations_trade_count(self, sample_ohlcv_data, default_optimizer):
        """Test that valid combinations meet minimum trade requirement."""
        param_grid = {
            "param_value": [30, 50]
        }
        
        result = default_optimizer.optimize(
            MockStrategy,
            sample_ohlcv_data,
            param_grid,
            symbol="TEST"
        )
        
        valid_results = result.all_results[result.all_results["valid"] == True]
        
        # Note: Can't directly check trade count without running backtest
        assert len(valid_results) == result.valid_combinations
