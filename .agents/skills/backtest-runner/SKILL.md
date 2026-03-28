---
name: backtest-runner
description: Use when running backtests on trading strategies, comparing multiple strategies, or visualizing backtest results.
---

# Backtest Runner Skill

This skill provides comprehensive backtesting capabilities for trading strategies with support for multi-strategy comparison, results visualization, and detailed performance analysis.

## When to Use This Skill

- Running backtests on trading strategies
- Comparing multiple strategies side-by-side
- Generating equity curves and trade visualizations
- Validating strategy performance before live trading
- Analyzing trade-by-trade breakdown
- Simulating realistic trading conditions

## What This Skill Does

1. **Strategy Backtesting**: Simulates trading on historical data
2. **Multi-Strategy Comparison**: Compares performance across strategies
3. **Results Visualization**: Generates equity curves and performance charts
4. **Trade Analysis**: Detailed breakdown of individual trades
5. **Realistic Simulation**: Includes commission, slippage, position sizing
6. **Performance Metrics**: Comprehensive risk-adjusted returns

## How to Use

### Basic Backtest
```
Run a backtest on the RSI strategy for AAPL from 2023-01-01 to 2024-01-01
```

### Multi-Strategy Comparison
```
Compare RSI, MACD, and Bollinger strategies on SPY
Backtest period: 2022-01-01 to 2024-01-01
```

### With Custom Settings
```
Backtest momentum strategy on QQQ
Initial capital: $100,000
Commission: 0.1%
Slippage: 0.05%
Position size: 50%
```

### Batch Backtesting
```
Run backtests for these symbols: AAPL, GOOGL, MSFT
Use the MACD strategy
Period: Last 2 years
```

## Configuration Options

### BacktestConfig Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| initial_capital | 100,000 | Starting capital |
| commission | 0.001 | Commission rate (0.1%) |
| slippage | 0.0005 | Slippage rate (0.05%) |
| position_size | 1.0 | Position size fraction |
| risk_free_rate | 0.0 | Risk-free rate for Sharpe |

### Trading Costs

```
Commission: 0.1% per trade
Slippage: 0.05% price impact
These can significantly affect high-frequency strategies
```

## Output Format

### BacktestResult

```
{
    strategy_name: 'RSIStrategy',
    symbol: 'AAPL',
    start_date: '2023-01-03',
    end_date: '2023-12-29',
    initial_capital: 100000.0,
    final_capital: 124500.0,
    total_return: 0.245,
    total_trades: 45,
    winning_trades: 26,
    losing_trades: 19,
    win_rate: 0.58,
    profit_factor: 1.82,
    max_drawdown: -0.12,
    max_drawdown_pct: 0.12,
    sharpe_ratio: 1.45,
    sortino_ratio: 1.92,
    trades: [Trade, ...],
    equity_curve: Series
}
```

### Trade Record

```
{
    entry_date: '2023-03-15',
    exit_date: '2023-03-22',
    entry_price: 155.50,
    exit_price: 158.25,
    quantity: 100,
    side: 'long',
    pnl: 265.0,
    return_pct: 0.0177,
    commission: 1.56
}
```

## Performance Metrics

### Returns
| Metric | Description |
|--------|-------------|
| Total Return | Overall percentage return |
| Annualized Return | Return normalized to yearly |
| CAGR | Compound annual growth rate |

### Trading Statistics
| Metric | Description |
|--------|-------------|
| Total Trades | Number of round-trip trades |
| Win Rate | Percentage of winning trades |
| Profit Factor | Gross profit / gross loss |
| Avg Trade Return | Mean return per trade |
| Avg Winning Trade | Mean profit of winners |
| Avg Losing Trade | Mean loss of losers |

### Risk Metrics
| Metric | Description |
|--------|-------------|
| Sharpe Ratio | Risk-adjusted return |
| Sortino Ratio | Downside risk-adjusted return |
| Max Drawdown | Largest peak-to-trough |
| Max Drawdown % | Max drawdown as percentage |

## Examples

### Example 1: Simple Backtest

**User**: "Run a backtest on RSI strategy for AAPL 2023"

**Output**:
```
=== Backtest Results: RSIStrategy ===

Symbol: AAPL
Period: 2023-01-03 to 2023-12-29
Initial Capital: $100,000.00

Performance:
  Total Return: +24.5%
  Final Capital: $124,500.00
  Max Drawdown: -12.3%

Trading:
  Total Trades: 45
  Win Rate: 57.8%
  Profit Factor: 1.82
  Avg Trade: +0.54%

Risk-Adjusted:
  Sharpe Ratio: 1.45
  Sortino Ratio: 1.92

Trade Summary:
  Winners: 26 trades | Avg: +$312.50
  Losers: 19 trades | Avg: -$171.05

Equity Curve:
  Start: $100,000
  Peak: $130,000
  Trough: $110,000
  End: $124,500
```

### Example 2: Multi-Strategy Comparison

**User**: "Compare RSI, MACD, and Bollinger strategies on SPY"

**Output**:
```
=== Strategy Comparison ===

Symbols: SPY
Period: 2022-01-01 to 2024-01-01
Initial Capital: $100,000

┌─────────────────┬───────────┬───────────┬───────────┐
│ Metric          │ RSI       │ MACD      │ Bollinger │
├─────────────────┼───────────┼───────────┼───────────┤
│ Total Return    │ 18.2%     │ 12.5%     │ 22.1%     │
│ Sharpe Ratio    │ 1.32      │ 0.95      │ 1.58      │
│ Max Drawdown    │ -8.5%     │ -15.2%    │ -10.3%    │
│ Win Rate        │ 58.2%     │ 52.1%     │ 61.5%     │
│ Profit Factor   │ 1.65      │ 1.28      │ 1.95      │
│ Total Trades    │ 38        │ 24        │ 52        │
│ Sortino Ratio   │ 1.71      │ 1.15      │ 2.10      │
└─────────────────┴───────────┴───────────┴───────────┘

Ranking:
  1. Bollinger Strategy (Sharpe: 1.58, Return: 22.1%)
  2. RSI Strategy (Sharpe: 1.32, Return: 18.2%)
  3. MACD Strategy (Sharpe: 0.95, Return: 12.5%)

Recommendation: Bollinger shows best risk-adjusted performance
```

### Example 3: Detailed Trade Analysis

**User**: "Show me the trade breakdown for the momentum strategy"

**Output**:
```
=== Trade Breakdown: MomentumStrategy ===

Total Trades: 67

Trade Duration Distribution:
  < 1 day:  12 trades (18%)
  1-5 days: 28 trades (42%)
  5-10 days: 15 trades (22%)
  > 10 days: 12 trades (18%)

Return Distribution:
  Winners (>5%): 8 trades
  Small Winners (0-5%): 28 trades
  Small Losers (0 to -5%): 24 trades
  Large Losers (<-5%): 7 trades

Largest Winners:
  #1: +$1,245 (12.3%, held 15 days)
  #2: +$980 (9.8%, held 8 days)
  #3: +$875 (8.2%, held 22 days)

Largest Losers:
  #1: -$890 (-7.2%, held 18 days)
  #2: -$720 (-6.5%, held 5 days)
  #3: -$650 (-5.8%, held 12 days)

Consecutive Results:
  Max Consecutive Wins: 8
  Max Consecutive Losses: 4
```

### Example 4: Batch Backtest

**User**: "Run backtests for AAPL, GOOGL, MSFT using RSI strategy"

**Output**:
```
=== Batch Backtest ===

Strategy: RSIStrategy
Period: 2023-01-01 to 2024-01-01

┌─────────┬──────────┬───────────┬──────────┬─────────┬────────┐
│ Symbol  │ Return   │ Sharpe    │ Trades   │ Win%    │ Max DD │
├─────────┼──────────┼───────────┼──────────┼─────────┼────────┤
│ AAPL    │ +24.5%   │ 1.45       │ 45       │ 57.8%   │ -12.3% │
│ GOOGL   │ +18.2%   │ 1.12       │ 38       │ 55.2%   │ -14.1% │
│ MSFT    │ +28.7%   │ 1.68       │ 52       │ 60.5%   │ -9.8%  │
└─────────┴──────────┴───────────┴──────────┴─────────┴────────┘

Summary:
  Average Return: 23.8%
  Best Performer: MSFT (+28.7%)
  Worst Performer: GOOGL (+18.2%)
  Average Sharpe: 1.42
```

## Visualization Options

### Available Charts

| Chart | Description |
|-------|-------------|
| Equity Curve | Portfolio value over time |
| Drawdown Chart | Drawdown periods visualization |
| Trade Points | Entry/exit points on price |
| Returns Distribution | Histogram of trade returns |
| Rolling Sharpe | Rolling risk-adjusted returns |

### Example Visualization Request

```
Generate equity curve and drawdown chart for the backtest
Mark entry/exit points on the price chart
```

## Technical Details

**Implementation Module**: `trading_system.backtesting`

**Key Classes**:
- `BacktestEngine` - Main backtesting engine
- `BacktestConfig` - Configuration for backtests
- `BacktestResult` - Results container
- `Trade` - Individual trade record

**Dependencies**: pandas, numpy, matplotlib

**Usage**:
```python
from trading_system.backtesting import BacktestEngine, BacktestConfig

config = BacktestConfig(
    initial_capital=100000,
    commission=0.001,
    slippage=0.0005
)
engine = BacktestEngine(config)
result = engine.run(strategy, data, "AAPL")
print(result.summary())
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Ignoring trading costs | Always include commission and slippage |
| Survivorship bias | Use historical universe data |
| Look-ahead bias | Use only available data at each point |
| Overfitting | Validate with out-of-sample testing |
| Ignoring drawdown | Check max drawdown, not just returns |

## Tips

- Always include realistic trading costs
- Use out-of-sample testing to validate
- Check drawdown, not just returns
- Compare multiple strategies for robustness
- Review individual trade quality
- Consider position sizing impact
- Validate with different market conditions

## Related Skills

- `strategy-optimizer` - Optimize parameters before backtesting
- `metrics-calculator` - Calculate detailed performance metrics
- `risk-analyzer` - Analyze portfolio risk and position sizing
- `data-fetcher` - Fetch historical data for backtesting

---

**Version**: 1.0.0
**Last Updated**: 2026-03-19
**Maintained By**: Trading Team
