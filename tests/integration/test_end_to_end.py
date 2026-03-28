"""
End-to-end integration tests for the complete trading system workflow.

Tests the complete workflow:
- Fetch -> Validate -> Cache
- Optimize -> Backtest -> Report
- Multi-symbol portfolio analysis
- Full system integration

Run with: pytest tests/integration/test_end_to_end.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import json

from trading_system.data.fetchers.mock_fetcher import MockDataFetcher
from trading_system.data.storage.cache import CacheManager, InMemoryCache
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
def trading_config():
    """Trading system configuration."""
    return {
        "initial_capital": 100000,
        "commission": 0.001,
        "slippage": 0.0005,
        "position_size": 1.0,
        "risk_free_rate": 0.02,
    }


@pytest.fixture
def optimization_config():
    """Optimization configuration."""
    return {
        "metric": MetricType.SHARPE_RATIO,
        "maximize": True,
        "min_trades_per_fold": 3,
        "verbose": False,
    }


@pytest.fixture
def walk_forward_config():
    """Walk-forward configuration."""
    return {
        "window_type": WindowType.ROLLING,
        "train_window": 200,
        "test_window": 50,
        "step_size": 50,
        "verbose": False,
    }


@pytest.fixture
def sample_portfolio_data():
    """Generate sample portfolio data for multiple symbols."""
    np.random.seed(42)
    
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    data_dict = {}
    
    for i, symbol in enumerate(symbols):
        dates = pd.date_range(start="2022-01-01", periods=400, freq="D")
        
        # Different characteristics for each symbol
        base = 100 * (1 + i * 0.2)
        trend = np.linspace(0, 50 + i * 10, 400)  # Different trends
        returns = np.random.normal(0.0003, 0.02, 400)  # Different volatility
        prices = base * (1 + returns).cumprod() + trend
        
        data_dict[symbol] = pd.DataFrame({
            "open": prices * (1 + np.random.uniform(-0.005, 0.005, 400)),
            "high": prices * (1 + np.abs(np.random.uniform(0.005, 0.02, 400))),
            "low": prices * (1 - np.abs(np.random.uniform(0.005, 0.02, 400))),
            "close": prices,
            "volume": np.random.randint(5_000_000, 25_000_000, 400)
        }, index=dates)
    
    return data_dict


@pytest.fixture
def long_term_test_data():
    """Generate long-term test data for comprehensive testing."""
    dates = pd.date_range(start="2021-01-01", periods=600, freq="D")
    np.random.seed(42)
    
    # Complex price series with trends and cycles
    t = np.linspace(0, 6 * np.pi, 600)
    trend = np.linspace(0, 60, 600)  # Upward trend
    cycle = 20 * np.sin(t / 2)  # Medium-term cycles
    returns = np.random.normal(0.0003, 0.015, 600)
    noise = np.random.randn(600) * 3
    
    prices = 100 * (1 + returns).cumprod() + trend + cycle + noise
    
    return pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.005, 0.005, 600)),
        "high": prices * (1 + np.abs(np.random.uniform(0.005, 0.02, 600))),
        "low": prices * (1 - np.abs(np.random.uniform(0.005, 0.02, 600))),
        "close": prices,
        "volume": np.random.randint(5_000_000, 25_000_000, 600)
    }, index=dates)


# =============================================================================
# Test Complete Workflow: Fetch -> Optimize -> Backtest -> Report
# =============================================================================

class TestCompleteWorkflow:
    """Tests for complete workflow from data fetch to reporting."""

    def test_full_trading_pipeline(self, mock_data_fetcher, trading_config, optimization_config):
        """Test complete trading pipeline from fetch to report."""
        # Step 1: Data Fetch
        data = mock_data_fetcher.fetch("AAPL", "2022-01-01", "2023-09-01")
        assert len(data) > 0
        
        # Step 2: Data Validation
        validator = DataValidator()
        validator.validate_ohlcv(data)
        quality = validator.check_data_quality(data)
        assert quality.is_acceptable
        
        # Step 3: Parameter Optimization
        opt_config = OptimizationConfig(**optimization_config)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [65, 70, 75],
            "oversold": [25, 30, 35],
        }
        
        opt_result = optimizer.optimize(
            RSIStrategy,
            data,
            param_grid=param_grid,
            symbol="PIPELINE"
        )
        
        assert opt_result.best_params is not None
        assert opt_result.valid_combinations > 0
        
        # Step 4: Create optimized strategy
        best_config = RSIStrategyConfig(**opt_result.best_params)
        optimized_strategy = RSIStrategy(best_config)
        
        # Step 5: Run final backtest
        bt_config = BacktestConfig(**trading_config)
        engine = BacktestEngine(bt_config)
        final_result = engine.run(optimized_strategy, data, "FINAL")
        
        # Step 6: Generate report
        report = {
            "symbol": "AAPL",
            "period": f"{data.index[0].date()} to {data.index[-1].date()}",
            "optimization": {
                "best_params": opt_result.best_params,
                "best_score": opt_result.best_score,
                "combinations_tested": opt_result.total_combinations,
            },
            "backtest": {
                "total_return": final_result.total_return,
                "sharpe_ratio": final_result.sharpe_ratio,
                "max_drawdown": final_result.max_drawdown_pct,
                "total_trades": final_result.total_trades,
                "win_rate": final_result.win_rate,
            }
        }
        
        # Verify report structure
        assert "symbol" in report
        assert "optimization" in report
        assert "backtest" in report
        assert report["backtest"]["total_trades"] >= 0

    def test_multi_strategy_optimization_pipeline(self, mock_data_fetcher, trading_config):
        """Test optimization pipeline with multiple strategies."""
        # Fetch data once
        data = mock_data_fetcher.fetch("AAPL", "2022-01-01", "2023-06-01")
        
        # Define strategies and their parameter grids
        strategies = [
            ("RSI", RSIStrategy, {
                "period": [10, 14, 20],
                "overbought": [70],
                "oversold": [30],
            }),
            ("MACD", MACDStrategy, {}),  # No parameters to optimize
        ]
        
        engine = BacktestEngine(BacktestConfig(**trading_config))
        results = {}
        
        for name, strategy_class, param_grid in strategies:
            if param_grid:
                # Optimize
                opt_config = OptimizationConfig(verbose=False)
                optimizer = StrategyOptimizer(optimization_config=opt_config)
                opt_result = optimizer.optimize(
                    strategy_class,
                    data,
                    param_grid=param_grid,
                    symbol=name
                )
                best_params = opt_result.best_params
            else:
                # Use defaults
                best_params = {}
            
            # Create strategy with best/default params
            if strategy_class == RSIStrategy and best_params:
                strategy = strategy_class(RSIStrategyConfig(**best_params))
            else:
                strategy = strategy_class()
            
            # Backtest
            result = engine.run(strategy, data, name)
            
            results[name] = {
                "params": best_params,
                "return": result.total_return,
                "sharpe": result.sharpe_ratio,
                "trades": result.total_trades,
            }
        
        # All strategies should have results
        assert len(results) == 2
        assert "RSI" in results
        assert "MACD" in results


# =============================================================================
# Test Portfolio Workflow
# =============================================================================

class TestPortfolioWorkflow:
    """Tests for portfolio-level workflow."""

    def test_portfolio_backtest_workflow(self, sample_portfolio_data, trading_config):
        """Test backtesting a portfolio of symbols."""
        # Configure
        engine = BacktestEngine(BacktestConfig(**trading_config))
        strategy = RSIStrategy()
        
        # Run backtest for each symbol
        symbol_results = {}
        
        for symbol, data in sample_portfolio_data.items():
            result = engine.run(strategy, data, symbol)
            symbol_results[symbol] = {
                "return": result.total_return,
                "sharpe": result.sharpe_ratio,
                "max_dd": result.max_drawdown_pct,
                "trades": result.total_trades,
                "win_rate": result.win_rate,
                "final_capital": result.final_capital,
            }
        
        # Verify all symbols processed
        assert len(symbol_results) == len(sample_portfolio_data)
        
        # Calculate portfolio metrics
        total_return = sum(r["return"] for r in symbol_results.values()) / len(symbol_results)
        avg_sharpe = np.mean([r["sharpe"] for r in symbol_results.values()])
        
        assert total_return is not None
        assert avg_sharpe is not None

    def test_portfolio_optimization_workflow(self, sample_portfolio_data, optimization_config):
        """Test optimizing strategy for portfolio."""
        # Use one symbol as representative for optimization
        representative_symbol = "AAPL"
        data = sample_portfolio_data[representative_symbol]
        
        # Optimize
        opt_config = OptimizationConfig(**optimization_config)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [65, 70, 75],
            "oversold": [25, 30, 35],
        }
        
        opt_result = optimizer.optimize(
            RSIStrategy,
            data,
            param_grid=param_grid,
            symbol=representative_symbol
        )
        
        # Apply optimized parameters to all symbols
        engine = BacktestEngine(BacktestConfig())
        best_config = RSIStrategyConfig(**opt_result.best_params)
        optimized_strategy = RSIStrategy(best_config)
        
        portfolio_results = {}
        for symbol, symbol_data in sample_portfolio_data.items():
            result = engine.run(optimized_strategy, symbol_data, symbol)
            portfolio_results[symbol] = result.total_return
        
        # All symbols should have results
        assert len(portfolio_results) == len(sample_portfolio_data)

    def test_portfolio_walk_forward_analysis(self, sample_portfolio_data, walk_forward_config):
        """Test walk-forward analysis for portfolio."""
        # Use one symbol for walk-forward
        representative_symbol = "AAPL"
        data = sample_portfolio_data[representative_symbol]
        
        wf_config = WalkForwardConfig(**walk_forward_config)
        wf_optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        wf_result = wf_optimizer.optimize(
            RSIStrategy,
            data,
            param_grid=param_grid,
            symbol=representative_symbol
        )
        
        # Get robust parameters
        robust_params = wf_result.get_robust_params()
        
        # Apply to all symbols
        engine = BacktestEngine(BacktestConfig())
        strategy = RSIStrategy(RSIStrategyConfig(**robust_params))
        
        oos_returns = []
        for symbol, symbol_data in sample_portfolio_data.items():
            # Split data for OOS test
            split_idx = int(len(symbol_data) * 0.7)
            oos_data = symbol_data.iloc[split_idx:]
            
            result = engine.run(strategy, oos_data, symbol)
            oos_returns.append(result.total_return)
        
        assert len(oos_returns) == len(sample_portfolio_data)


# =============================================================================
# Test Walk-Forward End-to-End
# =============================================================================

class TestWalkForwardEndToEnd:
    """Tests for end-to-end walk-forward analysis."""

    def test_complete_walk_forward_pipeline(self, long_term_test_data, optimization_config, walk_forward_config):
        """Test complete walk-forward analysis pipeline."""
        # Step 1: Define parameter grid
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [65, 70, 75],
            "oversold": [25, 30, 35],
        }
        
        # Step 2: Configure walk-forward
        wf_config = WalkForwardConfig(**walk_forward_config)
        wf_optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
        
        # Step 3: Run walk-forward analysis
        wf_result = wf_optimizer.optimize(
            RSIStrategy,
            long_term_test_data,
            param_grid=param_grid,
            symbol="WF_E2E"
        )
        
        # Step 4: Extract results
        robust_params = wf_result.get_robust_params()
        valid_periods = wf_result.get_valid_periods()
        
        # Step 5: Generate report
        report = {
            "total_periods": wf_result.total_periods,
            "valid_periods": len(valid_periods),
            "stability_score": wf_result.stability_score,
            "walk_forward_return": wf_result.walk_forward_return,
            "degradation_ratio": wf_result.degradation_ratio,
            "robustness_score": wf_result.robustness_score,
            "robust_params": robust_params,
        }
        
        # Verify report
        assert report["total_periods"] >= 0
        assert report["robustness_score"] >= 0
        assert isinstance(robust_params, dict)

    def test_walk_forward_comparison(self, long_term_test_data, walk_forward_config):
        """Test comparing walk-forward results for different strategies."""
        strategies = [
            ("RSI", RSIStrategy),
            ("MACD", MACDStrategy),
        ]
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        wf_config = WalkForwardConfig(**walk_forward_config)
        
        results = {}
        for name, strategy_class in strategies:
            wf_optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
            
            result = wf_optimizer.optimize(
                strategy_class,
                long_term_test_data,
                param_grid=param_grid,
                symbol=name
            )
            
            results[name] = {
                "stability": result.stability_score,
                "wfr": result.walk_forward_return,
                "robustness": result.robustness_score,
            }
        
        # Both strategies should have results
        assert len(results) == 2


# =============================================================================
# Test System Integration
# =============================================================================

class TestSystemIntegration:
    """Tests for complete system integration."""

    def test_data_pipeline_integration(self, mock_data_fetcher):
        """Test complete data pipeline."""
        # Create cache manager
        cache = CacheManager(ttl=3600, max_size=100)
        validator = DataValidator()
        
        # Fetch with caching
        fetcher = MockDataFetcher(cache=cache, seed=42)
        
        # First fetch - from "API"
        data1 = fetcher.fetch("AAPL", "2023-01-01", "2023-06-01")
        
        # Second fetch - from cache
        data2 = fetcher.fetch("AAPL", "2023-01-01", "2023-06-01")
        
        # Verify both are same
        assert len(data1) == len(data2)
        
        # Validate
        validator.validate_ohlcv(data1)
        quality = validator.check_data_quality(data1)
        assert quality.is_acceptable

    def test_optimization_backtest_integration(self, mock_data_fetcher, optimization_config):
        """Test integration between optimization and backtesting."""
        data = mock_data_fetcher.fetch("AAPL", "2022-01-01", "2023-06-01")
        
        # Optimize
        opt_config = OptimizationConfig(**optimization_config)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [70],
            "oversold": [30],
        }
        
        opt_result = optimizer.optimize(
            RSIStrategy,
            data,
            param_grid=param_grid,
            symbol="INT"
        )
        
        # Backtest with optimized params
        best_config = RSIStrategyConfig(**opt_result.best_params)
        strategy = RSIStrategy(best_config)
        
        engine = BacktestEngine()
        result = engine.run(strategy, data, "INT")
        
        # Optimization and backtest should be consistent
        assert result.total_trades >= 0

    def test_multi_source_fallback_integration(self):
        """Test multi-source data fallback."""
        # Primary source (mock)
        primary = MockDataFetcher(seed=100)
        
        # Secondary source (mock with different seed)
        secondary = MockDataFetcher(seed=200)
        
        # Fetch from primary
        data_primary = primary.fetch("AAPL", "2023-01-01", "2023-03-01")
        
        # Simulate primary failure and fallback to secondary
        try:
            # Try primary first
            if len(data_primary) == 0:
                data_secondary = secondary.fetch("AAPL", "2023-01-01", "2023-03-01")
                data = data_secondary
            else:
                data = data_primary
        except Exception:
            data = secondary.fetch("AAPL", "2023-01-01", "2023-03-01")
        
        # Should have valid data from one source
        assert len(data) > 0

    def test_error_recovery_workflow(self, mock_data_fetcher, trading_config):
        """Test error recovery in complete workflow."""
        # Normal workflow
        data = mock_data_fetcher.fetch("AAPL", "2023-01-01", "2023-09-01")
        
        # Validate
        validator = DataValidator()
        try:
            validator.validate_ohlcv(data)
        except Exception as e:
            pytest.fail(f"Validation failed: {e}")
        
        # Optimize (may produce no valid combinations)
        opt_config = OptimizationConfig(
            min_trades_per_fold=1000,  # Unrealistic high minimum
            verbose=False
        )
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "period": [14],
            "overbought": [70],
            "oversold": [30],
        }
        
        opt_result = optimizer.optimize(
            RSIStrategy,
            data,
            param_grid=param_grid,
            symbol="RECOVERY"
        )
        
        # If optimization fails, use default parameters
        if opt_result.valid_combinations == 0:
            best_params = {"period": 14, "overbought": 70, "oversold": 30}
        else:
            best_params = opt_result.best_params
        
        # Backtest with available parameters
        best_config = RSIStrategyConfig(**best_params)
        strategy = RSIStrategy(best_config)
        
        engine = BacktestEngine(BacktestConfig(**trading_config))
        result = engine.run(strategy, data, "RECOVERY")
        
        # Should always produce a result
        assert result is not None


# =============================================================================
# Test Reporting Integration
# =============================================================================

class TestReportingIntegration:
    """Tests for reporting functionality."""

    def test_generate_optimization_report(self, long_term_test_data, optimization_config):
        """Test generating optimization report."""
        opt_config = OptimizationConfig(**optimization_config)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [65, 70, 75],
            "oversold": [25, 30, 35],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_test_data,
            param_grid=param_grid,
            symbol="REPORT"
        )
        
        # Generate report
        report = {
            "metric": result.best_metric.value,
            "best_score": result.best_score,
            "best_params": result.best_params,
            "total_combinations": result.total_combinations,
            "valid_combinations": result.valid_combinations,
            "optimization_time": result.optimization_time,
            "top_5": result.top_n(5).to_dict("records") if len(result.top_n(5)) > 0 else [],
        }
        
        assert "metric" in report
        assert "best_params" in report
        assert report["total_combinations"] == 27

    def test_generate_backtest_report(self, sample_portfolio_data, trading_config):
        """Test generating backtest report for portfolio."""
        engine = BacktestEngine(BacktestConfig(**trading_config))
        strategy = RSIStrategy()
        
        report = {
            "symbols": {},
            "summary": {},
        }
        
        for symbol, data in sample_portfolio_data.items():
            result = engine.run(strategy, data, symbol)
            report["symbols"][symbol] = {
                "return": result.total_return,
                "sharpe": result.sharpe_ratio,
                "max_dd": result.max_drawdown_pct,
                "trades": result.total_trades,
                "win_rate": result.win_rate,
            }
        
        # Calculate summary
        returns = [s["return"] for s in report["symbols"].values()]
        sharpes = [s["sharpe"] for s in report["symbols"].values()]
        
        report["summary"] = {
            "avg_return": np.mean(returns),
            "avg_sharpe": np.mean(sharpes),
            "best_symbol": max(report["symbols"].items(), key=lambda x: x[1]["sharpe"])[0],
        }
        
        assert "symbols" in report
        assert "summary" in report

    def test_generate_walk_forward_report(self, long_term_test_data, walk_forward_config):
        """Test generating walk-forward analysis report."""
        wf_config = WalkForwardConfig(**walk_forward_config)
        wf_optimizer = WalkForwardOptimizer(walk_forward_config=wf_config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = wf_optimizer.optimize(
            RSIStrategy,
            long_term_test_data,
            param_grid=param_grid,
            symbol="WF_REPORT"
        )
        
        # Generate report
        report = {
            "window_type": result.window_type.value,
            "total_periods": result.total_periods,
            "valid_periods": len(result.get_valid_periods()),
            "stability_score": result.stability_score,
            "walk_forward_return": result.walk_forward_return,
            "degradation_ratio": result.degradation_ratio,
            "robustness_score": result.robustness_score,
            "robust_params": result.get_robust_params(),
        }
        
        assert "robustness_score" in report
        assert isinstance(report["robust_params"], dict)


# =============================================================================
# Test Performance Benchmarks
# =============================================================================

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_optimization_performance(self, long_term_test_data):
        """Test optimization performance with large parameter grid."""
        import time
        
        param_grid = {
            "period": [10, 14, 20, 25, 30],
            "overbought": [60, 65, 70, 75, 80],
            "oversold": [20, 25, 30, 35, 40],
        }
        
        opt_config = OptimizationConfig(verbose=False)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        start_time = time.time()
        
        result = optimizer.optimize(
            RSIStrategy,
            long_term_test_data,
            param_grid=param_grid,
            symbol="PERF"
        )
        
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert elapsed_time < 60  # Less than 1 minute
        assert result.total_combinations == 125  # 5 * 5 * 5

    def test_backtest_performance(self, sample_portfolio_data):
        """Test backtest performance across portfolio."""
        import time
        
        engine = BacktestEngine()
        strategy = RSIStrategy()
        
        start_time = time.time()
        
        for symbol, data in sample_portfolio_data.items():
            engine.run(strategy, data, symbol)
        
        elapsed_time = time.time() - start_time
        
        # Should complete quickly
        assert elapsed_time < 10  # Less than 10 seconds


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in the complete workflow."""

    def test_empty_data_handling(self):
        """Test handling of empty or minimal data."""
        fetcher = MockDataFetcher(seed=42)
        
        # Try to fetch minimal data
        try:
            data = fetcher.fetch("AAPL", "2023-01-01", "2023-01-02")
            # Should handle gracefully
            assert len(data) >= 0
        except Exception:
            # Exception is also acceptable for insufficient data
            pass

    def test_single_symbol_optimization(self):
        """Test optimization with single parameter combination."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        data = pd.DataFrame({
            "close": np.linspace(100, 110, 100),
            "volume": 1000000
        }, index=dates)
        
        param_grid = {
            "period": [14],  # Single value
            "overbought": [70],
            "oversold": [30],
        }
        
        opt_config = OptimizationConfig(verbose=False)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        result = optimizer.optimize(
            RSIStrategy,
            data,
            param_grid=param_grid,
            symbol="SINGLE"
        )
        
        # Should still produce result
        assert result.total_combinations >= 1

    def test_all_invalid_combinations_handling(self):
        """Test handling when all parameter combinations are invalid."""
        dates = pd.date_range(start="2023-01-01", periods=20, freq="D")
        data = pd.DataFrame({
            "close": np.linspace(100, 105, 20),
            "volume": 1000000
        }, index=dates)
        
        param_grid = {
            "period": [1000],  # Invalid for short data
            "overbought": [70],
            "oversold": [30],
        }
        
        opt_config = OptimizationConfig(min_trades_per_fold=100, verbose=False)
        optimizer = StrategyOptimizer(optimization_config=opt_config)
        
        result = optimizer.optimize(
            RSIStrategy,
            data,
            param_grid=param_grid,
            symbol="INVALID"
        )
        
        # Should handle gracefully
        assert result.valid_combinations == 0
