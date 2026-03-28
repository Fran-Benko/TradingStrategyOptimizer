---
name: metrics-calculator
description: Use when calculating trading performance metrics like Sharpe ratio, drawdown analysis, trade statistics, or risk-adjusted returns.
---

# Metrics Calculator Skill

This skill provides comprehensive performance metrics calculation for trading strategies, including risk-adjusted returns, drawdown analysis, trade statistics, and portfolio-level metrics.

## When to Use This Skill

- Calculating Sharpe, Sortino, or Calmar ratios
- Analyzing drawdown periods and recovery
- Computing trade statistics and distributions
- Evaluating risk-adjusted performance
- Generating performance reports
- Comparing strategy metrics
- Portfolio performance analysis

## What This Skill Does

1. **Risk-Adjusted Returns**: Sharpe, Sortino, Calmar ratios
2. **Drawdown Analysis**: Max drawdown, duration, recovery
3. **Trade Statistics**: Win rate, profit factor, expectancy
4. **Performance Attribution**: Returns decomposition
5. **Rolling Metrics**: Time-varying performance measures
6. **Portfolio Metrics**: Combined portfolio performance
7. **Benchmark Comparison**: Alpha, beta, information ratio

## How to Use

### Calculate Basic Metrics
```
Calculate performance metrics for this backtest result
```

### Detailed Analysis
```
Generate full metrics report including drawdown analysis
Show Sharpe, Sortino, Calmar, win rate, profit factor
```

### Trade Statistics
```
Analyze the trade log and calculate trade statistics
Distribution of trade returns, duration, and PnL
```

### Rolling Metrics
```
Calculate rolling 30-day Sharpe ratio for the equity curve
```

## Metric Categories

### Risk-Adjusted Returns

| Metric | Formula | Good Value |
|--------|---------|------------|
| Sharpe Ratio | (Return - Rf) / StdDev | > 1.0 |
| Sortino Ratio | (Return - Rf) / DownsideStd | > 1.5 |
| Calmar Ratio | Annual Return / Max DD | > 1.0 |
| Information Ratio | Alpha / Tracking Error | > 0.5 |

### Drawdown Metrics

| Metric | Description |
|--------|-------------|
| Max Drawdown | Largest peak-to-trough decline |
| Max Drawdown Duration | Longest time in drawdown |
| Recovery Time | Average time to recover |
| Drawdown Frequency | How often drawdowns occur |
| Average Drawdown | Mean drawdown depth |

### Trade Statistics

| Metric | Formula | Good Value |
|--------|---------|------------|
| Win Rate | Winners / Total Trades | > 50% |
| Profit Factor | Gross Profit / Gross Loss | > 1.5 |
| Expectancy | (Win% × AvgWin) - (Loss% × AvgLoss) | > 0 |
| R-Multiple | Trade P&L / Max Adverse Excursion | > 1.0 |
| Avg Trade | Mean P&L per trade | > 0 |
| Avg Winner | Mean P&L of winners | > 0 |
| Avg Loser | Mean P&L of losers | < 0 |

### Return Metrics

| Metric | Description |
|--------|-------------|
| Total Return | Overall percentage return |
| Annualized Return | Yearly normalized return |
| CAGR | Compound annual growth rate |
| Monthly Returns | Monthly performance breakdown |
| Rolling Returns | Time-windowed returns |

## Drawdown Analysis

### Drawdown Components

```
Max Drawdown: -15.2%
Max Drawdown Duration: 45 days
Average Drawdown: -6.8%
Drawdown Recovery: 12 days average
```

### Drawdown Timeline

```
Peak: Jan 15, 2023 ($125,000)
Trough: Feb 28, 2023 ($106,000)
Recovery: Mar 15, 2023 ($125,000)
Duration: 60 days
Depth: -15.2%
```

## Trade Distribution Analysis

### Return Distribution

| Percentile | Return |
|------------|--------|
| 95th | +8.5% |
| 75th | +3.2% |
| 50th (Median) | +0.8% |
| 25th | -1.5% |
| 5th | -5.2% |

### Trade Duration Distribution

| Duration | Count | Percentage |
|----------|-------|------------|
| Intraday | 12 | 18% |
| 1-5 days | 28 | 42% |
| 5-10 days | 15 | 22% |
| > 10 days | 12 | 18% |

## Rolling Metrics

### Rolling Sharpe Calculation

```python
# 30-day rolling Sharpe
rolling_sharpe = returns.rolling(30).apply(
    lambda x: (x.mean() - rf) / x.std() * sqrt(252)
)
```

### Rolling Drawdown

```python
# Calculate running drawdown
cumulative = (1 + returns).cumprod()
running_max = cumulative.expanding().max()
drawdown = (cumulative - running_max) / running_max
```

## Output Format

### Complete Metrics Report

```
=== Performance Metrics Report ===

Return Metrics:
  Total Return: +24.5%
  Annualized Return: 22.1%
  CAGR: 21.8%
  Monthly Return: +1.85% (avg)
  Best Month: +8.2%
  Worst Month: -4.1%

Risk-Adjusted Metrics:
  Sharpe Ratio: 1.45
  Sortino Ratio: 1.92
  Calmar Ratio: 1.52
  Information Ratio: 0.85

Drawdown Analysis:
  Max Drawdown: -12.3%
  Max DD Duration: 45 days
  Average Drawdown: -5.8%
  DD Recovery Time: 18 days avg
  Drawdown Count: 4

Trading Statistics:
  Total Trades: 67
  Win Rate: 58.2%
  Profit Factor: 1.82
  Expectancy: $185 per trade
  Avg Trade: +0.54%
  Avg Winner: +$420
  Avg Loser: -$185
  Largest Winner: +$1,245
  Largest Loser: -$890

Trade Distribution:
  Winners (>5%): 8 trades (12%)
  Small Winners (0-5%): 31 trades (46%)
  Small Losers (0 to -5%): 22 trades (33%)
  Large Losers (<-5%): 6 trades (9%)
```

## Examples

### Example 1: Basic Metrics Calculation

**User**: "Calculate all performance metrics for this backtest"

**Output**:
```
=== Performance Metrics ===

Risk-Adjusted Returns:
  Sharpe Ratio: 1.45
  Sortino Ratio: 1.92
  Calmar Ratio: 1.52

Drawdown Analysis:
  Max Drawdown: -12.3%
  Max DD Duration: 45 days
  Recovery Time: 18 days

Trading Statistics:
  Win Rate: 58.2%
  Profit Factor: 1.82
  Expectancy: $185/trade

Recommendation: Strong risk-adjusted performance with acceptable drawdown
```

### Example 2: Detailed Drawdown Analysis

**User**: "Analyze the drawdown periods in detail"

**Output**:
```
=== Drawdown Analysis ===

Major Drawdown Periods:

#1: Jan 15 - Feb 28, 2023 (45 days)
  Peak: $125,000
  Trough: $106,000
  Recovery: Mar 15, 2023
  Depth: -15.2%

#2: Jun 10 - Jul 20, 2023 (40 days)
  Peak: $130,000
  Trough: $115,000
  Recovery: Aug 5, 2023
  Depth: -11.5%

#3: Nov 1 - Nov 25, 2023 (24 days)
  Peak: $135,000
  Trough: $125,000
  Recovery: Dec 1, 2023
  Depth: -7.4%

Statistics:
  Average Drawdown Depth: -5.8%
  Average Drawdown Duration: 25 days
  Total Drawdown Periods: 4
  Longest Drawdown: 45 days
```

### Example 3: Trade Distribution Analysis

**User**: "Analyze the trade distribution and statistics"

**Output**:
```
=== Trade Distribution Analysis ===

Trade Count: 67 trades
  Winners: 39 trades (58.2%)
  Losers: 28 trades (41.8%)

Return Distribution:
  Mean: +0.54%
  Median: +0.35%
  Std Dev: 2.1%
  Skewness: +0.32 (slight positive)
  Kurtosis: 3.8

Percentiles:
  95th: +5.2%
  75th: +2.1%
  50th: +0.35%
  25th: -0.85%
  5th: -3.2%

Consecutive Results:
  Max Wins: 8 (avg: $320/trade)
  Max Losses: 4 (avg: -$150/trade)
  
Expectancy Analysis:
  Win Rate × Avg Win: 0.582 × $420 = $244
  Loss Rate × Avg Loss: 0.418 × $185 = $77
  Expectancy: $244 - $77 = $167/trade
```

### Example 4: Rolling Metrics

**User**: "Calculate rolling 30-day Sharpe and Sortino ratios"

**Output**:
```
=== Rolling Risk Metrics (30-day windows) ===

Sharpe Ratio Over Time:
  Average: 1.45
  Min: 0.52
  Max: 2.31
  Current: 1.62

Sortino Ratio Over Time:
  Average: 1.92
  Min: 0.68
  Max: 3.15
  Current: 2.24

Volatility Regime:
  High Vol (>20% annualized): 3 months
  Normal Vol (10-20%): 7 months
  Low Vol (<10%): 2 months

Drawdown Regime Analysis:
  Time in Drawdown: 35%
  Time at New Highs: 65%
```

## Technical Details

**Implementation Module**: `trading_system.optimization`

**Key Functions**:
- `StrategyOptimizer._extract_metrics()` - Extract metrics from backtest
- `BacktestEngine._sharpe_ratio()` - Sharpe calculation
- `BacktestEngine._sortino_ratio()` - Sortino calculation
- `BacktestResult` - Results with all metrics

**Dependencies**: pandas, numpy, scipy

**Usage**:
```python
from trading_system.optimization import MetricType

# From backtest result
sharpe = result.sharpe_ratio
sortino = result.sortino_ratio
max_dd = result.max_drawdown_pct
win_rate = result.win_rate

# Available metrics
metrics = [
    result.sharpe_ratio,
    result.sortino_ratio,
    result.total_return,
    result.win_rate,
    result.profit_factor,
    result.max_drawdown_pct,
]
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Ignoring downside deviation | Use Sortino instead of Sharpe |
| Only looking at returns | Always check risk metrics |
| Ignoring drawdown duration | Analyze time in drawdown |
| Cherry-picking time periods | Use full history for metrics |
| Ignoring trade distribution | Check distribution tails |

## Tips

- Always report both absolute and risk-adjusted returns
- Include drawdown analysis for risk context
- Check metric stability over time
- Compare against appropriate benchmarks
- Use multiple metrics for complete picture
- Validate metrics with out-of-sample data
- Consider transaction costs in analysis

## Related Skills

- `backtest-runner` - Generate results to analyze
- `strategy-optimizer` - Optimize for specific metrics
- `risk-analyzer` - Analyze portfolio-level risk

---

**Version**: 1.0.0
**Last Updated**: 2026-03-19
**Maintained By**: Trading Team
