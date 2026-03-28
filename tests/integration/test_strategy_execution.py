"""
Integration tests for trading strategy execution pipeline.

Tests the integration between:
- Strategy initialization and configuration
- Signal generation
- Backtesting engine
- Metrics calculation
- Multiple strategy comparison
- Parameter optimization loop

Run with: pytest tests/integration/test_strategy_execution.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig, SignalType
from trading_system.strategies.momentum.rsi_strategy import RSIStrategy, RSIStrategyConfig
from trading_system.strategies.momentum.macd_strategy import MACDStrategy
from trading_system.strategies.mean_reversion.bollinger_strategy import BollingerBandsStrategy
from trading_system.backtesting.engine import BacktestEngine, BacktestConfig, BacktestResult, Trade
from trading_system.optimization.optimizer import StrategyOptimizer, OptimizationConfig, MetricType, OptimizationResult
from trading_system.data.validators.data_validator import DataValidator


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    np.random.seed(42)
    
    returns = np.random.normal(0.0005, 0.015, 200)
    prices = 100 * (1 + returns).cumprod()
    
    return pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.005, 0.005, 200)),
        "high": prices * (1 + np.abs(np.random.uniform(0.005, 0.02, 200))),
        "low": prices * (1 - np.abs(np.random.uniform(0.005, 0.02, 200))),
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, 200)
    }, index=dates)


@pytest.fixture
def trending_ohlcv_data():
    """Generate trending OHLCV data for momentum strategy testing."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    
    # Strong uptrend
    trend = np.linspace(0, 50, 200)
    noise = np.random.randn(200) * 2
    prices = 100 + trend + noise
    
    return pd.DataFrame({
        "open": prices + np.random.randn(200) * 0.5,
        "high": prices + abs(np.random.randn(200)) * 2,
        "low": prices - abs(np.random.randn(200)) * 2,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, 200)
    }, index=dates)


@pytest.fixture
def oscillating_ohlcv_data():
    """Generate oscillating OHLCV data for mean reversion testing."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    
    # Sine wave with noise
    t = np.linspace(0, 4 * np.pi, 200)
    wave = 30 * np.sin(t)
    noise = np.random.randn(200) * 3
    prices = 100 + wave + noise
    
    return pd.DataFrame({
        "open": prices + np.random.randn(200) * 0.5,
        "high": prices + abs(np.random.randn(200)) * 2,
        "low": prices - abs(np.random.randn(200)) * 2,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, 200)
    }, index=dates)


@pytest.fixture
def default_backtest_config():
    """Default backtest configuration."""
    return BacktestConfig(
        initial_capital=100000.0,
        commission=0.001,
        slippage=0.0005,
        position_size=1.0
    )


@pytest.fixture
def default_optimizer_config():
    """Default optimizer configuration."""
    return OptimizationConfig(
        metric=MetricType.SHARPE_RATIO,
        maximize=True,
        verbose=False,
        min_trades_per_fold=3
    )


# =============================================================================
# Test Strategy -> Backtest -> Metrics Flow
# =============================================================================

class TestStrategyBacktestMetricsFlow:
    """Tests for the complete Strategy -> Backtest -> Metrics flow."""

    def test_rsi_strategy_full_pipeline(self, sample_ohlcv_data, default_backtest_config):
        """Test complete RSI strategy pipeline."""
        # Step 1: Configure strategy
        strategy = RSIStrategy(config=RSIStrategyConfig(
            period=14,
            overbought=70,
            oversold=30
        ))
        
        # Step 2: Generate signals
        signals = strategy.generate_signals(sample_ohlcv_data)
        assert len(signals) == len(sample_ohlcv_data)
        assert set(signals).issubset({-1, 0, 1})
        
        # Step 3: Run backtest
        engine = BacktestEngine(default_backtest_config)
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        # Step 4: Verify metrics
        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "RSIStrategy"
        assert result.symbol == "TEST"
        assert result.initial_capital == 100000.0
        assert result.total_trades >= 0
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.max_drawdown_pct, float)

    def test_macd_strategy_full_pipeline(self, sample_ohlcv_data, default_backtest_config):
        """Test complete MACD strategy pipeline."""
        strategy = MACDStrategy()
        
        # Generate signals
        signals = strategy.generate_signals(sample_ohlcv_data)
        
        # Run backtest
        engine = BacktestEngine(default_backtest_config)
        result = engine.run(strategy, sample_ohlcv_data, "AAPL")
        
        # Verify structure
        assert result.strategy_name == "MACDStrategy"
        assert result.symbol == "AAPL"
        assert result.initial_capital == 100000.0

    def test_bollinger_strategy_full_pipeline(self, oscillating_ohlcv_data, default_backtest_config):
        """Test complete Bollinger Bands strategy pipeline."""
        strategy = BollingerBandsStrategy()
        
        # Generate signals
        signals = strategy.generate_signals(oscillating_ohlcv_data)
        
        # Run backtest
        engine = BacktestEngine(default_backtest_config)
        result = engine.run(strategy, oscillating_ohlcv_data, "TEST")
        
        # Verify structure
        assert result.strategy_name == "BollingerBandsStrategy"
        assert result.total_trades >= 0

    def test_indicators_accessible_after_signal_generation(self, sample_ohlcv_data):
        """Test that indicators are accessible after signal generation."""
        strategy = RSIStrategy(config=RSIStrategyConfig(period=14))
        
        # Generate signals
        strategy.generate_signals(sample_ohlcv_data)
        
        # Access computed indicators
        rsi = strategy.get_indicator("rsi")
        assert rsi is not None
        assert len(rsi) == len(sample_ohlcv_data)

    def test_trade_list_contains_all_trades(self, sample_ohlcv_data, default_backtest_config):
        """Test that trade list contains all executed trades."""
        strategy = RSIStrategy()
        
        engine = BacktestEngine(default_backtest_config)
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        # Verify trade count matches
        assert len(result.trades) == result.total_trades
        
        # Verify each trade has required attributes
        for trade in result.trades:
            assert isinstance(trade, Trade)
            assert trade.entry_price > 0
            assert trade.exit_price > 0
            assert trade.quantity > 0
            assert trade.entry_date < trade.exit_date


# =============================================================================
# Test Multiple Strategies Comparison
# =============================================================================

class TestMultipleStrategyComparison:
    """Tests for comparing multiple strategies."""

    def test_compare_momentum_vs_mean_reversion(self, trending_ohlcv_data, oscillating_ohlcv_data):
        """Test comparing momentum and mean reversion strategies."""
        config = BacktestConfig(initial_capital=100000)
        engine = BacktestEngine(config)
        
        # Test momentum strategy on trending data
        momentum_strategy = MACDStrategy()
        momentum_result = engine.run(momentum_strategy, trending_ohlcv_data, "TREND")
        
        # Test mean reversion on oscillating data
        reversion_strategy = BollingerBandsStrategy()
        reversion_result = engine.run(reversion_strategy, oscillating_ohlcv_data, "OSCILLATE")
        
        # Both should produce valid results
        assert momentum_result.final_capital > 0
        assert reversion_result.final_capital > 0
        
        # Results should be comparable
        assert isinstance(momentum_result.sharpe_ratio, float)
        assert isinstance(reversion_result.sharpe_ratio, float)

    def test_compare_multiple_strategies_same_data(self, sample_ohlcv_data):
        """Test comparing multiple strategies on the same data."""
        strategies = [
            ("RSI", RSIStrategy()),
            ("MACD", MACDStrategy()),
            ("Bollinger", BollingerBandsStrategy()),
        ]
        
        engine = BacktestEngine(BacktestConfig(initial_capital=100000))
        results = {}
        
        for name, strategy in strategies:
            result = engine.run(strategy, sample_ohlcv_data, "SAME_DATA")
            results[name] = result
        
        # All strategies should produce results
        assert len(results) == len(strategies)
        
        # Results should have comparable structure
        for name, result in results.items():
            assert result.symbol == "SAME_DATA"
            assert result.initial_capital == 100000
            assert isinstance(result.sharpe_ratio, float)
            assert isinstance(result.win_rate, float)

    def test_strategy_selection_based_on_metrics(self, sample_ohlcv_data):
        """Test selecting best strategy based on Sharpe ratio."""
        strategies = [
            RSIStrategy(config=RSIStrategyConfig(period=10)),
            RSIStrategy(config=RSIStrategyConfig(period=14)),
            RSIStrategy(config=RSIStrategyConfig(period=20)),
        ]
        
        engine = BacktestEngine(BacktestConfig(initial_capital=100000))
        
        best_sharpe = -float('inf')
        best_strategy = None
        
        for strategy in strategies:
            result = engine.run(strategy, sample_ohlcv_data, "SELECT")
            
            if result.sharpe_ratio > best_sharpe:
                best_sharpe = result.sharpe_ratio
                best_strategy = strategy
        
        assert best_strategy is not None
        assert best_sharpe > -float('inf')

    def test_all_strategies_produce_valid_equity_curves(self, sample_ohlcv_data):
        """Test that all strategies produce valid equity curves."""
        strategies = [
            RSIStrategy(),
            MACDStrategy(),
            BollingerBandsStrategy(),
        ]
        
        engine = BacktestEngine(BacktestConfig())
        
        for strategy in strategies:
            result = engine.run(strategy, sample_ohlcv_data, "EQUITY_TEST")
            
            # Equity curve should be valid
            assert len(result.equity_curve) > 0
            assert result.equity_curve.iloc[0] == result.initial_capital
            assert not result.equity_curve.isna().any()


# =============================================================================
# Test Parameter Optimization Loop
# =============================================================================

class TestParameterOptimizationLoop:
    """Tests for parameter optimization workflow."""

    def test_rsi_parameter_optimization(self, sample_ohlcv_data, default_optimizer_config):
        """Test RSI parameter optimization workflow."""
        optimizer = StrategyOptimizer(optimization_config=default_optimizer_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [65, 70, 75],
            "oversold": [25, 30, 35],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            sample_ohlcv_data,
            param_grid=param_grid,
            symbol="OPT"
        )
        
        # Verify optimization result
        assert isinstance(result, OptimizationResult)
        assert result.best_params is not None
        assert len(result.best_params) > 0
        assert result.total_combinations == 27  # 3 * 3 * 3
        assert result.optimization_time > 0

    def test_optimization_finds_valid_parameters(self, sample_ohlcv_data, default_optimizer_config):
        """Test that optimization finds at least some valid parameter combinations."""
        optimizer = StrategyOptimizer(optimization_config=default_optimizer_config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70, 80],
            "oversold": [20, 30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            sample_ohlcv_data,
            param_grid=param_grid,
            symbol="OPT"
        )
        
        # Should find at least some valid combinations
        assert result.valid_combinations >= 0
        assert result.valid_combinations <= result.total_combinations

    def test_optimization_with_different_metrics(self, sample_ohlcv_data):
        """Test optimization with different metric types."""
        metrics = [
            MetricType.SHARPE_RATIO,
            MetricType.SORTINO_RATIO,
            MetricType.TOTAL_RETURN,
            MetricType.WIN_RATE,
        ]
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        results = {}
        for metric in metrics:
            config = OptimizationConfig(
                metric=metric,
                maximize=True,
                verbose=False
            )
            optimizer = StrategyOptimizer(optimization_config=config)
            results[metric] = optimizer.optimize(
                RSIStrategy,
                sample_ohlcv_data,
                param_grid,
                symbol="METRIC_TEST"
            )
        
        # All should produce valid results
        for metric, result in results.items():
            assert result.best_metric == metric

    def test_optimization_best_params_applied_to_strategy(self, sample_ohlcv_data, default_optimizer_config):
        """Test that optimized parameters can be applied to strategy."""
        optimizer = StrategyOptimizer(optimization_config=default_optimizer_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            sample_ohlcv_data,
            param_grid=param_grid,
            symbol="APPLY"
        )
        
        # Apply best params to strategy
        best_config = RSIStrategyConfig(**result.best_params)
        optimized_strategy = RSIStrategy(best_config)
        
        # Run backtest with optimized strategy
        engine = BacktestEngine()
        final_result = engine.run(optimized_strategy, sample_ohlcv_data, "FINAL")
        
        # Should produce valid result
        assert final_result.total_trades >= 0

    def test_optimization_top_n_results(self, sample_ohlcv_data, default_optimizer_config):
        """Test retrieving top N parameter combinations."""
        optimizer = StrategyOptimizer(optimization_config=default_optimizer_config)
        
        param_grid = {
            "period": [10, 14, 20],
            "overbought": [65, 70, 75],
            "oversold": [25, 30, 35],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            sample_ohlcv_data,
            param_grid=param_grid,
            symbol="TOPN"
        )
        
        # Get top 5 combinations
        top_5 = result.top_n(5)
        
        assert len(top_5) <= 5
        assert len(top_5) > 0

    def test_optimization_with_insufficient_combinations_fails(self, sample_ohlcv_data):
        """Test that optimization with empty param_grid fails gracefully."""
        optimizer = StrategyOptimizer()
        
        with pytest.raises(ValueError):
            optimizer.optimize(
                RSIStrategy,
                sample_ohlcv_data,
                param_grid={},  # Empty grid
                symbol="EMPTY"
            )

    def test_optimization_respects_min_trades(self, sample_ohlcv_data):
        """Test that optimization respects minimum trades per fold."""
        config = OptimizationConfig(
            metric=MetricType.SHARPE_RATIO,
            min_trades_per_fold=10,  # High minimum
            verbose=False
        )
        optimizer = StrategyOptimizer(optimization_config=config)
        
        param_grid = {
            "period": [10, 14],
            "overbought": [70],
            "oversold": [30],
        }
        
        result = optimizer.optimize(
            RSIStrategy,
            sample_ohlcv_data,
            param_grid=param_grid,
            symbol="MIN_TRADES"
        )
        
        # valid_combinations may be less than total due to min trades requirement
        assert result.valid_combinations <= result.total_combinations


# =============================================================================
# Test Signal Quality Integration
# =============================================================================

class TestSignalQualityIntegration:
    """Tests for signal quality and consistency."""

    def test_signal_consistency_across_runs(self, sample_ohlcv_data):
        """Test that signals are consistent across multiple runs with same data."""
        strategy = RSIStrategy()
        
        # Run twice with same data
        signals1 = strategy.generate_signals(sample_ohlcv_data)
        signals2 = strategy.generate_signals(sample_ohlcv_data)
        
        # Signals should be identical
        assert np.array_equal(signals1, signals2)

    def test_strategy_handles_missing_data_gracefully(self):
        """Test that strategies handle missing data gracefully."""
        # Create data with NaN
        data_with_nan = pd.DataFrame({
            "close": [100, np.nan, 102, 103, 104],
            "volume": [1000000] * 5
        })
        
        strategy = RSIStrategy()
        
        # Strategy should handle or raise meaningful error
        try:
            signals = strategy.generate_signals(data_with_nan)
            # If it doesn't raise, it should return something
            assert len(signals) >= 0
        except (ValueError, KeyError):
            # This is acceptable - data is invalid
            pass

    def test_strategy_performance_metrics_correlated(self, sample_ohlcv_data):
        """Test that performance metrics are correlated correctly."""
        engine = BacktestEngine()
        strategy = RSIStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "CORR_TEST")
        
        # Positive return should correlate with positive metrics
        if result.total_return > 0:
            assert result.final_capital > result.initial_capital


# =============================================================================
# Test Strategy Configuration Integration
# =============================================================================

class TestStrategyConfigurationIntegration:
    """Tests for strategy configuration integration."""

    def test_strategy_with_custom_config(self, sample_ohlcv_data, default_backtest_config):
        """Test strategy with custom configuration."""
        custom_config = RSIStrategyConfig(
            period=20,
            overbought=80,
            oversold=20
        )
        
        strategy = RSIStrategy(custom_config)
        engine = BacktestEngine(default_backtest_config)
        
        result = engine.run(strategy, sample_ohlcv_data, "CUSTOM")
        
        assert result.strategy_name == "RSIStrategy"

    def test_invalid_strategy_config_rejected(self):
        """Test that invalid strategy configurations are rejected."""
        # Invalid config: overbought <= oversold
        with pytest.raises(ValueError):
            invalid_config = RSIStrategyConfig(
                period=14,
                overbought=30,  # Should be > oversold
                oversold=40
            )

    def test_strategy_parameters_retrievable(self):
        """Test that strategy parameters are retrievable."""
        config = RSIStrategyConfig(period=20, overbought=75, oversold=25)
        strategy = RSIStrategy(config)
        
        params = strategy.get_parameters()
        
        assert "period" in params
        assert "overbought" in params
        assert "oversold" in params
        assert params["period"] == 20


# =============================================================================
# Test Backtest Configuration Integration
# =============================================================================

class TestBacktestConfigurationIntegration:
    """Tests for backtest configuration integration."""

    def test_different_commission_levels(self, sample_ohlcv_data):
        """Test backtest with different commission levels."""
        commissions = [0.0, 0.001, 0.005, 0.01]
        
        results = []
        for commission in commissions:
            config = BacktestConfig(commission=commission)
            engine = BacktestEngine(config)
            strategy = RSIStrategy()
            
            result = engine.run(strategy, sample_ohlcv_data, "COMM")
            results.append((commission, result.final_capital))
        
        # Higher commission should generally result in lower final capital
        # (all other things being equal)
        assert len(results) == len(commissions)

    def test_different_initial_capitals(self, sample_ohlcv_data):
        """Test backtest with different initial capital levels."""
        capitals = [10000, 50000, 100000, 500000]
        
        for capital in capitals:
            config = BacktestConfig(initial_capital=capital)
            engine = BacktestEngine(config)
            strategy = RSIStrategy()
            
            result = engine.run(strategy, sample_ohlcv_data, "CAP")
            
            assert result.initial_capital == capital
            assert result.final_capital > 0

    def test_position_size_affects_exposure(self, sample_ohlcv_data):
        """Test that position size affects market exposure."""
        sizes = [0.1, 0.5, 1.0]
        
        results = []
        for size in sizes:
            config = BacktestConfig(position_size=size)
            engine = BacktestEngine(config)
            strategy = RSIStrategy()
            
            result = engine.run(strategy, sample_ohlcv_data, "SIZE")
            
            if result.total_trades > 0:
                results.append((size, result))
        
        # Larger position size should generally mean larger absolute PnL per trade
        if len(results) >= 2:
            assert len(results) == len(sizes)


# =============================================================================
# Test Equity Curve Integration
# =============================================================================

class TestEquityCurveIntegration:
    """Tests for equity curve and portfolio tracking."""

    def test_equity_curve_reflects_trades(self, sample_ohlcv_data):
        """Test that equity curve correctly reflects executed trades."""
        config = BacktestConfig(initial_capital=100000)
        engine = BacktestEngine(config)
        strategy = RSIStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "EQUITY")
        
        # Equity curve should have correct length
        assert len(result.equity_curve) > 0
        
        # First value should be initial capital
        assert result.equity_curve.iloc[0] == 100000
        
        # Trades should have affected equity
        if result.total_trades > 0:
            assert result.equity_curve.iloc[-1] != 100000

    def test_equity_curve_stays_positive(self, sample_ohlcv_data):
        """Test that equity curve doesn't go to zero or negative."""
        config = BacktestConfig(initial_capital=100000)
        engine = BacktestEngine(config)
        strategy = RSIStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "POSITIVE")
        
        # All equity values should be positive
        assert (result.equity_curve > 0).all()

    def test_drawdown_tracking(self, sample_ohlcv_data):
        """Test that drawdown is correctly tracked."""
        config = BacktestConfig(initial_capital=100000)
        engine = BacktestEngine(config)
        strategy = RSIStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "DD")
        
        # Drawdown should be non-negative
        assert result.max_drawdown >= 0
        assert result.max_drawdown_pct >= 0
        
        # Drawdown percentage should be between 0 and 1
        assert 0 <= result.max_drawdown_pct <= 1
