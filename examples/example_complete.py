"""
Complete Trading System Example.

This example demonstrates the full workflow:
1. Data fetching with factory pattern
2. Data validation
3. Strategy optimization
4. Walk-forward analysis
5. Backtesting

Run: python examples/example_complete.py
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from trading_system.utils.logging import setup_logging, get_logger
from trading_system.utils.helpers import validate_date_range, calculate_returns
from trading_system.data.fetchers.factory import DataFetcherFactory
from trading_system.data.validators.data_validator import DataValidator
from trading_system.strategies import (
    RSIStrategy,
    MACDStrategy,
    BollingerBandsStrategy,
)
from trading_system.backtesting.engine import BacktestEngine, BacktestConfig
from trading_system.optimization import (
    StrategyOptimizer,
    MetricType,
    WalkForwardOptimizer,
    WindowType,
)


def generate_sample_data(days: int = 500) -> pd.DataFrame:
    """Generate realistic sample OHLCV data."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    
    np.random.seed(42)
    returns = np.random.normal(0.0003, 0.015, days)
    price = 150 * (1 + returns).cumprod()
    
    intraday = np.random.uniform(-0.008, 0.008, days)
    
    data = pd.DataFrame({
        "open": price * (1 + intraday * 0.3),
        "high": price * (1 + np.abs(intraday) * 0.7),
        "low": price * (1 - np.abs(intraday) * 0.7),
        "close": price,
        "volume": np.random.randint(5_000_000, 25_000_000, days)
    }, index=dates)
    
    data["high"] = data[["open", "high", "close"]].max(axis=1)
    data["low"] = data[["open", "low", "close"]].min(axis=1)
    
    return data


def main():
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("COMPLETE TRADING SYSTEM EXAMPLE")
    logger.info("=" * 60)
    
    data = generate_sample_data(500)
    logger.info(f"Generated {len(data)} days of sample data")
    logger.info(f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
    
    validator = DataValidator()
    quality = validator.check_data_quality(data)
    logger.info(f"Data quality score: {quality.quality_score}/100")
    
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: STRATEGY OPTIMIZATION")
    logger.info("=" * 60)
    
    optimizer = StrategyOptimizer(progress_callback=lambda i, t: 
        logger.info(f"Progress: {i}/{t}") if i % 10 == 0 else None)
    
    param_grid = {
        "period": [10, 14, 20],
        "overbought": [65, 70, 75],
        "oversold": [25, 30, 35],
    }
    
    logger.info(f"Optimizing RSI with {len(list(__import__('itertools').product(*param_grid.values())))} combinations")
    
    result = optimizer.optimize(
        RSIStrategy,
        data,
        param_grid=param_grid,
        metric=MetricType.SHARPE_RATIO,
        cv_folds=3
    )
    
    logger.info(f"Best params: {result.best_params}")
    logger.info(f"Best score: {result.best_score:.4f}")
    logger.info(f"Optimization time: {result.optimization_time:.2f}s")
    
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: WALK-FORWARD ANALYSIS")
    logger.info("=" * 60)
    
    wf_optimizer = WalkForwardOptimizer()
    wf_result = wf_optimizer.optimize(
        RSIStrategy,
        data,
        param_grid=param_grid,
        window_type=WindowType.ROLLING,
        train_window=252,
        test_window=63,
        metric=MetricType.SHARPE_RATIO
    )
    
    logger.info(f"Walk-forward return: {wf_result.walk_forward_return:.2%}")
    logger.info(f"Stability score: {wf_result.stability_score:.2f}")
    logger.info(f"Degradation ratio: {wf_result.degradation_ratio:.2f}")
    logger.info(f"Robustness score: {wf_result.robustness_score:.2f}")
    
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: MULTI-STRATEGY BACKTESTING")
    logger.info("=" * 60)
    
    engine = BacktestEngine(BacktestConfig(initial_capital=100_000))
    
    strategies = [
        ("RSI", RSIStrategy()),
        ("MACD", MACDStrategy()),
        ("Bollinger", BollingerBandsStrategy()),
    ]
    
    results = {}
    for name, strategy in strategies:
        try:
            result = engine.run(strategy, data, "SAMPLE")
            results[name] = result
            logger.info(f"\n{name}:")
            logger.info(f"  Return: {result.total_return:.2%}")
            logger.info(f"  Sharpe: {result.sharpe_ratio:.2f}")
            logger.info(f"  Trades: {result.total_trades}")
            logger.info(f"  Win Rate: {result.win_rate:.2%}")
        except Exception as e:
            logger.error(f"Error testing {name}: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: DATA FETCHER FACTORY")
    logger.info("=" * 60)
    
    factory = DataFetcherFactory()
    logger.info(f"Available sources: {factory.list_available_sources()}")
    
    mock_fetcher = factory.create("mock")
    test_data = mock_fetcher.fetch("TEST", "2023-01-01", "2023-12-31")
    logger.info(f"Mock fetcher returned {len(test_data)} rows")
    
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE COMPLETE")
    logger.info("=" * 60)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Strategy':<15} {'Return':>10} {'Sharpe':>8} {'Trades':>8}")
    print("-" * 60)
    for name, result in results.items():
        print(f"{name:<15} {result.total_return:>9.2%} {result.sharpe_ratio:>8.2f} {result.total_trades:>8}")
    print("-" * 60)
    print(f"Best Optimized: RSI with sharpe={result.best_score:.2f}")
    print(f"Walk-Forward Robustness: {wf_result.robustness_score:.2f}")


if __name__ == "__main__":
    main()
