"""
Demo script to test all trading strategies.

Run: python examples/demo_strategies.py
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from trading_system.strategies import (
    RSIStrategy,
    MACDStrategy,
    BollingerBandsStrategy,
    MeanReversionStrategy,
    TrendClassifierStrategy,
    MomentumMLStrategy,
)
from trading_system.backtesting.engine import BacktestEngine, BacktestConfig


def generate_sample_data(symbol: str = "AAPL", days: int = 252) -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.02, days)
    price = 100 * (1 + returns).cumprod()
    
    intraday = np.random.uniform(-0.01, 0.01, days)
    
    data = pd.DataFrame({
        "open": price * (1 + intraday * 0.3),
        "high": price * (1 + np.abs(intraday) * 0.8),
        "low": price * (1 - np.abs(intraday) * 0.8),
        "close": price,
        "volume": np.random.randint(1_000_000, 10_000_000, days)
    }, index=dates)
    
    data["high"] = data[["open", "high", "close"]].max(axis=1)
    data["low"] = data[["open", "low", "close"]].min(axis=1)
    
    return data


def test_strategy(strategy_name: str, strategy, data: pd.DataFrame, symbol: str):
    """Test a strategy and print results."""
    try:
        print(f"\n{'='*50}")
        print(f"Testing: {strategy_name}")
        print(f"{'='*50}")
        
        signals = strategy.generate_signals(data)
        
        buys = (signals == 1).sum()
        sells = (signals == -1).sum()
        print(f"Signals generated: {len(signals)}")
        print(f"  Buy signals:  {buys}")
        print(f"  Sell signals: {sells}")
        print(f"  Hold signals: {len(signals) - buys - sells}")
        
        config = BacktestConfig(initial_capital=100_000)
        engine = BacktestEngine(config)
        result = engine.run(strategy, data, symbol)
        
        print(f"\nBacktest Results:")
        print(f"  Total Return:     {result.total_return:.2%}")
        print(f"  Final Capital:    ${result.final_capital:,.2f}")
        print(f"  Max Drawdown:     {result.max_drawdown_pct:.2%}")
        print(f"  Sharpe Ratio:     {result.sharpe_ratio:.2f}")
        print(f"  Win Rate:         {result.win_rate:.2%}")
        print(f"  Total Trades:     {result.total_trades}")
        
        return True
    except Exception as e:
        print(f"Error testing {strategy_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("Trading System Strategy Demo")
    print("="*50)
    
    data = generate_sample_data(days=500)
    print(f"\nGenerated {len(data)} days of sample data")
    print(f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
    
    strategies = [
        ("RSI Strategy", RSIStrategy()),
        ("MACD Strategy", MACDStrategy()),
        ("Bollinger Bands Strategy", BollingerBandsStrategy()),
        ("Mean Reversion Strategy", MeanReversionStrategy()),
        ("Trend Classifier Strategy", TrendClassifierStrategy()),
        ("Momentum ML Strategy", MomentumMLStrategy()),
    ]
    
    results = {}
    for name, strategy in strategies:
        results[name] = test_strategy(name, strategy, data, "SAMPLE")
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"{'Strategy':<30} {'Return':>10} {'Sharpe':>8} {'Trades':>8}")
    print("-"*50)
    
    for name, success in results.items():
        if success:
            _, strategy = next(s for s in strategies if s[0] == name)
            try:
                signals = strategy.generate_signals(data)
                config = BacktestConfig()
                engine = BacktestEngine(config)
                result = engine.run(strategy, data, "SAMPLE")
                print(f"{name:<30} {result.total_return:>9.2%} {result.sharpe_ratio:>8.2f} {result.total_trades:>8}")
            except:
                print(f"{name:<30} {'N/A':>10}")
    
    print("\nDemo completed!")


if __name__ == "__main__":
    main()
