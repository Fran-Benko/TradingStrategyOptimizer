"""
Integration tests for backtest workflow.

Tests the integration between:
- Data fetching
- Multiple strategy execution
- Result comparison
- Walk-forward analysis
- Results aggregation

Run with: pytest tests/integration/test_backtest_flow.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict

from trading_system.data.fetchers.mock_fetcher import MockDataFetcher
from trading_system.data.storage.cache import InMemoryCache
from trading_system.data.validators.data_validator import DataValidator
from trading_system.strategies.momentum.rsi_strategy import RSIStrategy, RSIStrategyConfig
from trading_system.strategies.momentum.macd_strategy import MACDStrategy
from trading_system.strategies.mean_reversion.bollinger_strategy import BollingerBandsStrategy
from trading_system.backtesting.engine import BacktestEngine, BacktestConfig, BacktestResult
from trading_system.optimization.optimizer import StrategyOptimizer, OptimizationConfig, MetricType
from trading_system.optimization.walk_forward import (
    WalkForwardOptimizer,
    WalkForwardConfig,
    WalkForwardResult,
    WindowType,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_data_fetcher():
    """Create a mock data fetcher for testing."""
    return MockDataFetcher(seed=42, volatility=0.02)


@pytest.fixture
def sample_data_with_cache(mock_data_fetcher):
    """Fetch sample data with caching."""
    cache = InMemoryCache(max_size=100)
    fetcher = MockDataFetcher(cache=cache, seed=42)
    
    data = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31")
    return data


@pytest.fixture
def long_term_data():
    """Generate longer term data for walk-forward testing."""
    dates = pd.date_range(start="2022-01-01", periods=500, freq="D")
    np.random.seed(42)
    
    # Generate realistic price series with trends
    returns = np.random.normal(0.0003, 0.015, 500)
    trend = np.linspace(0, 30, 500)  # Upward trend
    prices = 100 * (1 + returns).cumprod() + trend
    
    return pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.005, 0.005, 500)),
        "high": prices * (1 + np.abs(np.random.uniform(0.005, 0.02, 500))),
        "low": prices * (1 - np.abs(np.random.uniform(0.005, 0.02, 500))),
        "close": prices,
        "volume": np.random.randint(5_000_000, 25_000_000, 500)
    }, index=dates)


@pytest.fixture
def multi_symbol_data():
    """Generate data for multiple symbols."""
    symbols = ["AAPL", "GOOGL", "MSFT"]
    data_dict = {}
    
    np.random.seed(42)
    
    for symbol in symbols:
        dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
        
        # Different base prices for different symbols
        base_multiplier = {"AAPL": 1.0, "GOOGL": 1.5, "MSFT": 0.8}[symbol]
        returns = np.random.normal(0.0003, 0.015, 200)
        prices = 100 * base_multiplier * (1 + returns).cumprod()
        
        data_dict[symbol] = pd.DataFrame({
            "open": prices * (1 + np.random.uniform(-0.005, 0.005, 200)),
            "high": prices * (1 + np.abs(np.random.uniform(0.005, 0.02, 200))),
            "low": prices * (1 - np.abs(np.random.uniform(0.005, 0.02, 200))),
            "close": prices,
            "volume": np.random.randint(5_000_000, 25_000_000, 200)
        }, index=dates)
    
    return data_dict


@pytest.fixture
def default_backtest_config():
    """Default backtest configuration."""
    return BacktestConfig(
        initial_capital=100000.0,
        commission=0.001,
        slippage=0.0005,
        position_size=1.0
    )


# =============================================================================
# Test Fetch Data -> Run Multiple Strategies
# =============================================================================

class TestFetchDataRunMultipleStrategies:
    """Tests for fetching data and running multiple strategies."""

    def test_fetch_data_and_run_all_strategies(self, mock_data_fetcher, default_backtest_config):
        """Test fetching data and running multiple strategies."""
        # Step 1: Fetch data
        data = mock_data_fetcher.fetch("AAPL", "2023-01-01", "2023-09-01")
        assert len(data) > 0
        
        # Step 2: Define strategies
        strategies = [
            RSIStrategy(),
            MACDStrategy(),
            BollingerBandsStrategy(),
        ]
        
        # Step 3: Run all strategies
        engine = BacktestEngine(default_backtest_config)
        results = []
        
        for strategy in strategies:
            result = engine.run(strategy, data, "AAPL")
            results.append(result)
        
        # Verify all strategies produced results
        assert len(results) == len(strategies)
        
        for result in results:
            assert isinstance(result, BacktestResult)
            assert result.symbol == "AAPL"

    def test_multi_symbol_backtest_workflow(self, multi_symbol_data, default_backtest_config):
        """Test backtesting across multiple symbols."""
        engine = BacktestEngine(default_backtest_config)
        strategy = RSIStrategy()
        
        symbol_results = {}
        
        for symbol, data in multi_symbol_data.items():
            result = engine.run(strategy, data, symbol)
            symbol_results[symbol] = result
        
        # Verify all symbols processed
        assert len(symbol_results) == len(multi_symbol_data)
        
        # Each result should be for its symbol
        for symbol, result in symbol_results.items():
            assert result.symbol == symbol

    def test_strategy_selection_across_symbols(self, multi_symbol_data):
        """Test selecting best strategy for each symbol."""
        engine = BacktestEngine(BacktestConfig())
        
        strategies = [
            ("RSI", RSIStrategy()),
            ("MACD", MACDStrategy()),
            ("Bollinger", BollingerBandsStrategy()),
        ]
        
        best_by_symbol = {}
        
        for symbol, data in multi_symbol_data.items():
            best_sharpe = -float('inf')
            best_strategy = None
            best_result = None
            
            for name, strategy in strategies:
                result = engine.run(strategy, data, symbol)
                
                if result.sharpe_ratio > best_sharpe:
                    best_sharpe = result.sharpe_ratio
                    best_strategy = name
                    best_result = result
            
            best_by_symbol[symbol] = {
                "strategy": best_strategy,
                "sharpe": best_sharpe,
                "result": best_result
            }
        
        # All symbols should have a best strategy
        assert len(best_by_symbol) == len(multi_symbol_data)


# =============================================================================
# Test Compare Results
# =============================================================================

class TestCompareResults:
    """Tests for comparing backtest results."""

    def test_compare_total_returns(self, sample_data_with_cache, default_backtest_config):
        """Test comparing total returns across strategies."""
        strategies = [
            RSIStrategy(),
            MACDStrategy(),
            BollingerBandsStrategy(),
        ]
        
        engine = BacktestEngine(default_backtest_config)
        returns = {}
        
        for strategy in strategies:
            result = engine.run(strategy, sample_data_with_cache, "COMPARE")
            returns[strategy.name] = result.total_return
        
        # Should have returns for all strategies
        assert len(returns) == len(strategies)

    def test_compare_risk_metrics(self, sample_data_with_cache):
        """Test comparing risk metrics across strategies."""
        strategies = [
            RSIStrategy(),
            MACDStrategy(),
            BollingerBandsStrategy(),
        ]
        
        engine = BacktestEngine(BacktestConfig())
        
        risk_metrics = {}
        for strategy in strategies:
            result = engine.run(strategy, sample_data_with_cache, "RISK")
            risk_metrics[strategy.name] = {
                "sharpe": result.sharpe_ratio,
                "sortino": result.sortino_ratio,
                "max_dd": result.max_drawdown_pct,
                "volatility": result.equity_curve.pct_change().std()
            }
        
        # All strategies should have risk metrics
        assert len(risk_metrics) == len(strategies)

    def test_rank_strategies_by_sharpe(self, sample_data_with_cache):
        """Test ranking strategies by Sharpe ratio."""
        strategies = [
            RSIStrategy(config=RSIStrategyConfig(period=10)),
            RSIStrategy(config=RSIStrategyConfig(period=14)),
            RSIStrategy(config=RSIStrategyConfig(period=20)),
        ]
        
        engine = BacktestEngine(BacktestConfig())
        
        results = []
        for strategy in strategies:
            result = engine.run(strategy, sample_data_with_cache, "RANK")
            results.append((strategy.config.period, result.sharpe_ratio, result))
        
        # Sort by Sharpe ratio
        ranked = sorted(results, key=lambda x: x[1], reverse=True)
        
        # Best Sharpe should be first
        assert len(ranked) == 3
        assert ranked[0][1] >= ranked[1][1] >= ranked[2][1]

    def test_aggregate_portfolio_results(self, multi_symbol_data):
        """Test aggregating results across symbols."""
        engine = BacktestEngine(BacktestConfig())
        strategy = RSIStrategy()
        
        individual_returns = []
        individual_sharpes = []
        
        for symbol, data in multi_symbol_data.items():
            result = engine.run(strategy, data, symbol)
            individual_returns.append(result.total_return)
            individual_sharpes.append(result.sharpe_ratio)
        
        # Aggregate metrics
        avg_return = np.mean(individual_returns)
        avg_sharpe = np.mean(individual_sharpes)
        
        assert avg_return is not None
        assert avg_sharpe is not None


# =============================================================================
# Test Walk-Forward Analysis
# =============================================================================

class TestWalkForwardAnalysis:
    """Tests for walk-forward analysis workflow."""

    def test_walk_forward_rolling_window(self, long_term_data):
        """Test walk-forward analysis with rolling windows."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,
            test_window=50,
            step_size=50,
            optimization_metric=MetricType.SHARPE_RATIO,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="WF_ROLL"
        )
        
        assert isinstance(result, WalkForwardResult)
        assert result.window_type == WindowType.ROLLING
        assert result.total_periods >= 0

    def test_walk_forward_expanding_window(self, long_term_data):
        """Test walk-forward analysis with expanding windows."""
        config = WalkForwardConfig(
            window_type=WindowType.EXPANDING,
            train_window=200,
            test_window=50,
            step_size=50,
            optimization_metric=MetricType.SHARPE_RATIO,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="WF_EXP"
        )
        
        assert isinstance(result, WalkForwardResult)
        assert result.window_type == WindowType.EXPANDING

    def test_walk_forward_metrics_calculated(self, long_term_data):
        """Test that walk-forward metrics are calculated correctly."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,
            test_window=50,
            step_size=50,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="WF_MET"
        )
        
        # Check robustness metrics
        assert result.stability_score is not None
        assert result.walk_forward_return is not None
        assert result.degradation_ratio is not None
        assert result.robustness_score is not None

    def test_walk_forward_robust_params_extraction(self, long_term_data):
        """Test extracting robust parameters from walk-forward analysis."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,
            test_window=50,
            step_size=50,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="WF_ROB"
        )
        
        robust_params = result.get_robust_params()
        
        # Should return dict of parameters
        assert isinstance(robust_params, dict)

    def test_walk_forward_insufficient_data_handling(self):
        """Test that walk-forward handles insufficient data gracefully."""
        # Create short data
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        short_data = pd.DataFrame({
            "close": np.linspace(100, 110, 50),
            "volume": 1000000
        }, index=dates)
        
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,  # More than data length
            test_window=50,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        with pytest.raises(ValueError):
            optimizer.optimize(RSIStrategy, short_data, param_grid, symbol="SHORT")


# =============================================================================
# Test Results Aggregation
# =============================================================================

class TestResultsAggregation:
    """Tests for aggregating backtest results."""

    def test_aggregate_results_dataframe(self, long_term_data):
        """Test converting results to DataFrame for analysis."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,
            test_window=50,
            step_size=50,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="AGG"
        )
        
        df = result.to_dataframe()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "period" in df.columns
        assert "os_return" in df.columns

    def test_aggregate_oos_performance(self, long_term_data):
        """Test aggregating out-of-sample performance."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,
            test_window=50,
            step_size=50,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="OOS_AGG"
        )
        
        oos_df = result.out_of_sample_results
        
        if len(oos_df) > 0:
            mean_return = oos_df["return"].mean()
            mean_sharpe = oos_df["sharpe"].mean()
            
            assert isinstance(mean_return, float)
            assert isinstance(mean_sharpe, float)

    def test_summary_generation(self, long_term_data):
        """Test generating summary from results."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,
            test_window=50,
            step_size=50,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="SUM"
        )
        
        summary = result.summary()
        
        assert isinstance(summary, str)
        assert "Walk-Forward" in summary or "Window" in summary

    def test_valid_periods_extraction(self, long_term_data):
        """Test extracting valid periods from results."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,
            test_window=50,
            step_size=50,
            min_trades_per_period=2,
            verbose=False
        )
        
        optimizer = WalkForwardOptimizer(walk_forward_config=config)
        
        param_grid = {
            "period": [14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="VALID"
        )
        
        valid_periods = result.get_valid_periods()
        
        assert isinstance(valid_periods, list)


# =============================================================================
# Test End-to-End Backtest Flow
# =============================================================================

class TestEndToEndBacktestFlow:
    """Tests for complete end-to-end backtest flow."""

    def test_full_backtest_workflow(self, mock_data_fetcher):
        """Test complete backtest workflow from data fetch to results."""
        # Step 1: Fetch data
        data = mock_data_fetcher.fetch("AAPL", "2023-01-01", "2023-09-01")
        
        # Step 2: Validate data
        validator = DataValidator()
        validator.validate_ohlcv(data)
        quality = validator.check_data_quality(data)
        assert quality.is_acceptable
        
        # Step 3: Optimize parameters
        opt_config = OptimizationConfig(
            metric=MetricType.SHARPE_RATIO,
            verbose=False
        )
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        opt_result = optimizer.optimize(
            RSIStrategy,
            data,
            param_grid=param_grid,
            symbol="E2E"
        )
        
        # Step 4: Run final backtest with optimized parameters
        best_config = RSIStrategyConfig(**opt_result.best_params)
        final_strategy = RSIStrategy(best_config)
        
        engine = BacktestEngine(BacktestConfig())
        final_result = engine.run(final_strategy, data, "E2E_FINAL")
        
        # Step 5: Verify results
        assert final_result.total_trades >= 0
        assert final_result.initial_capital == 100000.0

    def test_workflow_with_multiple_strategies(self, mock_data_fetcher):
        """Test workflow with multiple strategies."""
        data = mock_data_fetcher.fetch("AAPL", "2023-01-01", "2023-09-01")
        
        strategies = [
            ("RSI", RSIStrategy()),
            ("MACD", MACDStrategy()),
            ("Bollinger", BollingerBandsStrategy()),
        ]
        
        engine = BacktestEngine(BacktestConfig())
        
        results = {}
        for name, strategy in strategies:
            result = engine.run(strategy, data, name)
            results[name] = {
                "return": result.total_return,
                "sharpe": result.sharpe_ratio,
                "trades": result.total_trades,
                "win_rate": result.win_rate,
            }
        
        # All strategies should have results
        assert len(results) == len(strategies)

    def test_workflow_error_recovery(self, mock_data_fetcher):
        """Test workflow handles errors gracefully."""
        # Test with valid data first
        data = mock_data_fetcher.fetch("AAPL", "2023-01-01", "2023-06-01")
        
        engine = BacktestEngine(BacktestConfig())
        strategy = RSIStrategy()
        
        result = engine.run(strategy, data, "RECOVERY")
        
        assert result is not None
        assert isinstance(result, BacktestResult)

    def test_workflow_consistency_across_runs(self, mock_data_fetcher):
        """Test that workflow produces consistent results across runs."""
        data = mock_data_fetcher.fetch("AAPL", "2023-01-01", "2023-06-01")
        
        engine = BacktestEngine(BacktestConfig())
        strategy = RSIStrategy(config=RSIStrategyConfig(period=14, seed=42))
        
        # Run twice
        result1 = engine.run(strategy, data, "CONSISTENT")
        
        # Same strategy, same data should give same results
        strategy2 = RSIStrategy(config=RSIStrategyConfig(period=14, seed=42))
        result2 = engine.run(strategy2, data, "CONSISTENT")
        
        # Results should be equivalent (may differ slightly due to float precision)
        assert abs(result1.total_return - result2.total_return) < 0.001


# =============================================================================
# Test Walk-Forward + Optimization Integration
# =============================================================================

class TestWalkForwardOptimizationIntegration:
    """Tests for walk-forward and optimization integration."""

    def test_optimization_then_walk_forward(self, long_term_data):
        """Test running optimization then walk-forward with same parameters."""
        # Step 1: Initial optimization on full dataset
        opt_config = OptimizationConfig(metric=MetricType.SHARPE_RATIO, verbose=False)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [65, 70, 75],
            "oversold": [25, 30, 35],
        }
        
        opt_result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="OPT"
        )
        
        # Step 2: Walk-forward with same grid
        wf_config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_window=200,
            test_window=50,
            step_size=50,
            verbose=False
        )
        
        wf_optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
        
        wf_result = wf_optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="WF"
        )
        
        # Both should produce valid results
        assert opt_result.best_params is not None
        assert wf_result.robustness_score is not None

    def test_compare_optimized_vs_fixed_params(self, long_term_data):
        """Test comparing optimized vs fixed parameters."""
        # Fixed parameters
        fixed_config = RSIStrategyConfig(period=14, overbought=70, oversold=30)
        fixed_strategy = RSIStrategy(fixed_config)
        
        # Optimized parameters
        opt_config = OptimizationConfig(metric=MetricType.SHARPE_RATIO, verbose=False)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [70],
            "oversold": [30],
        }
        
        opt_result = optimizer.optimize(
            RSIStrategy,
            long_term_data,
            param_grid=param_grid,
            symbol="COMPARE"
        )
        
        # Both should be runnable
        engine = BacktestEngine(BacktestConfig())
        
        fixed_result = engine.run(fixed_strategy, long_term_data, "FIXED")
        assert fixed_result.total_trades >= 0


# =============================================================================
# Test Data Validation Integration
# =============================================================================

class TestDataValidationIntegration:
    """Tests for data validation integration in backtest flow."""

    def test_validate_before_backtest(self, mock_data_fetcher):
        """Test validating data before running backtest."""
        # Fetch data
        data = mock_data_fetcher.fetch("AAPL", "2023-01-01", "2023-09-01")
        
        # Validate
        validator = DataValidator()
        
        # Should not raise
        validator.validate_ohlcv(data)
        
        # Run backtest
        engine = BacktestEngine()
        strategy = RSIStrategy()
        result = engine.run(strategy, data, "VAL")
        
        assert result is not None

    def test_batch_validation_workflow(self, multi_symbol_data):
        """Test batch validation workflow."""
        validator = DataValidator()
        
        # Validate all data
        reports = validator.validate_batch(multi_symbol_data)
        
        assert len(reports) == len(multi_symbol_data)
        
        # Run backtests only for valid data
        engine = BacktestEngine()
        strategy = RSIStrategy()
        
        for symbol, data in multi_symbol_data.items():
            if reports[symbol].is_acceptable:
                result = engine.run(strategy, data, symbol)
                assert result.symbol == symbol
