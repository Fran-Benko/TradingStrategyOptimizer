---
name: strategy-optimizer
description: Use when optimizing trading strategy parameters with grid search, walk-forward analysis, or finding best parameters for backtesting.
---

# Strategy Optimizer Skill

This skill provides comprehensive parameter optimization for trading strategies using grid search and walk-forward analysis to find robust, optimal parameters.

## When to Use This Skill

- Finding optimal parameters for trading strategies
- Validating strategy robustness across different market conditions
- Preventing overfitting with walk-forward analysis
- Comparing multiple parameter combinations
- Cross-validation for strategy parameters
- Evaluating in-sample vs out-of-sample performance

## What This Skill Does

1. **Grid Search Optimization**: Exhaustive search over parameter grids
2. **Walk-Forward Analysis**: Validates robustness across market regimes
3. **Cross-Validation**: Prevents overfitting with multiple folds
4. **Multiple Metrics**: Optimizes Sharpe, Sortino, Calmar, returns, and more
5. **Best Parameter Selection**: Automatically selects optimal parameters
6. **Performance Tracking**: Detailed metrics for all combinations tested

## How to Use

### Basic Grid Search
```
Optimize RSI strategy parameters using grid search
Parameter grid: rsi_period [10, 14, 20], overbought [70, 80], oversold [20, 30]
Metric: Sharpe ratio
```

### Walk-Forward Analysis
```
Run walk-forward analysis on MACD strategy
Train window: 252 days, Test window: 63 days
Use rolling windows
```

### Custom Parameter Grid
```
Optimize Bollinger strategy with these parameters:
- bb_period: [15, 20, 25]
- bb_std: [1.5, 2.0, 2.5]
- exit_threshold: [0.5, 1.0, 1.5]
Metric: Sortino ratio
```

## Optimization Metrics

| Metric | Description | Optimize For |
|--------|-------------|--------------|
| Sharpe Ratio | Risk-adjusted returns | Maximize |
| Sortino Ratio | Downside risk-adjusted | Maximize |
| Total Return | Absolute return | Maximize |
| Win Rate | Percentage of winning trades | Maximize |
| Profit Factor | Gross profit / gross loss | Maximize |
| Calmar Ratio | Return / max drawdown | Maximize |
| Max Drawdown | Largest peak-to-trough | Minimize |

## Walk-Forward Analysis

### Window Types

**Rolling Window**:
- Fixed training period
- Moves forward with each period
- Better for non-stationary markets

**Expanding Window**:
- Grows over time
- Always uses all historical data
- Better for strategies that improve with data

### Configuration Options

```
Train Window: 252 days (1 year)
Test Window: 63 days (1 quarter)
Step Size: 63 days (monthly rebalancing)
Min Trades Per Period: 5
```

### Robustness Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| Stability Score | Consistency of OOS returns | > 0.7 |
| Degradation Ratio | OOS / IS performance | > 0.5 |
| Robustness Score | Composite robustness | > 0.6 |
| Walk-Forward Return | Overall OOS return | > 0 |

## Output Format

### OptimizationResult
```
{
    best_params: {'rsi_period': 14, 'overbought': 70, 'oversold': 30},
    best_score: 1.45,
    best_metric: 'sharpe_ratio',
    all_results: DataFrame,
    optimization_time: 45.2,
    total_combinations: 18,
    valid_combinations: 15
}
```

### WalkForwardResult
```
{
    window_type: 'rolling',
    total_periods: 12,
    stability_score: 0.82,
    walk_forward_return: 0.15,
    degradation_ratio: 0.68,
    robustness_score: 0.75,
    period_results: [PeriodResult, ...]
}
```

## Examples

### Example 1: Grid Search Optimization

**User**: "Optimize RSI strategy with grid search"

**Output**:
```
=== Grid Search Optimization ===

Strategy: RSIStrategy
Symbol: AAPL
Metric: Sharpe Ratio
Parameter Grid:
  - rsi_period: [10, 14, 20]
  - overbought: [70, 80]
  - oversold: [20, 30]

Results:
  Total Combinations: 18
  Valid Combinations: 15
  Optimization Time: 12.5s

Best Parameters:
  rsi_period: 14
  overbought: 70
  oversold: 30

Best Score: Sharpe Ratio = 1.85

Top 5 Configurations:
  # | RSI | OB  | OS  | Sharpe | Return | Win%
  1 | 14  | 70  | 30  | 1.85   | 24.5%  | 58%
  2 | 14  | 80  | 20  | 1.72   | 22.1%  | 55%
  3 | 20  | 70  | 30  | 1.65   | 20.8%  | 52%
```

### Example 2: Walk-Forward Analysis

**User**: "Run walk-forward analysis on the MACD strategy"

**Output**:
```
=== Walk-Forward Analysis ===

Strategy: MACDStrategy
Window Type: Rolling
Train Window: 252 days
Test Window: 63 days
Total Periods: 15

Robustness Metrics:
  Stability Score: 0.82
  Walk-Forward Return: 12.4%
  Degradation Ratio: 0.68
  Robustness Score: 0.75

Period Summary:
  Period 1: IS Sharpe=1.2, OOS Sharpe=0.9, Degradation=0.75
  Period 2: IS Sharpe=1.4, OOS Sharpe=1.1, Degradation=0.79
  Period 3: IS Sharpe=1.1, OOS Sharpe=0.8, Degradation=0.73
  ...

Best Robust Parameters:
  macd_fast: 12
  macd_slow: 26
  macd_signal: 9

Recommendation: Strategy shows moderate robustness.
  Consider parameter stability across periods.
```

### Example 3: Cross-Validation

**User**: "Run 5-fold cross-validation on Bollinger strategy"

**Output**:
```
=== Cross-Validation Optimization ===

Strategy: BollingerStrategy
CV Folds: 5
Metric: Sortino Ratio

Fold Results:
  Fold 1: Train=0.85, Test=0.72, Valid=True
  Fold 2: Train=0.91, Test=0.78, Valid=True
  Fold 3: Train=0.78, Test=0.65, Valid=True
  Fold 4: Train=0.88, Test=0.70, Valid=True
  Fold 5: Train=0.82, Test=0.74, Valid=True

CV Summary:
  Mean CV Score: 0.72 (+/- 0.05)
  Stability: High

Best Parameters (from Fold 4):
  bb_period: 20
  bb_std: 2.0
  exit_threshold: 1.0
```

## Technical Details

**Implementation Module**: `trading_system.optimization`

**Key Classes**:
- `StrategyOptimizer` - Grid search optimization
- `WalkForwardOptimizer` - Walk-forward analysis
- `OptimizationConfig` - Configuration for optimization
- `WalkForwardConfig` - Configuration for walk-forward
- `MetricType` - Supported optimization metrics
- `WindowType` - Rolling vs expanding windows

**Dependencies**: pandas, numpy, backtrader

**Usage**:
```python
from trading_system.optimization import StrategyOptimizer, WalkForwardOptimizer

# Grid search
optimizer = StrategyOptimizer()
result = optimizer.optimize(RSIStrategy, data, param_grid)

# Walk-forward
wf_optimizer = WalkForwardOptimizer()
wf_result = wf_optimizer.optimize(RSIStrategy, data, param_grid)
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Overfitting to historical data | Always use walk-forward validation |
| Too many parameter combinations | Start with coarse grid, refine |
| Ignoring stability | Check consistency across periods |
| Small sample sizes | Ensure minimum trades per period |
| Ignoring degradation | IS/OOS ratio should be > 0.5 |

## Tips

- Start with coarse grid search, then refine around best parameters
- Use walk-forward to validate robustness before live trading
- Cross-validation helps prevent overfitting
- Check parameter stability across walk-forward periods
- Combine multiple metrics for robust selection
- Consider transaction costs in optimization

## Related Skills

- `backtest-runner` - Run backtests with optimized parameters
- `metrics-calculator` - Calculate detailed performance metrics
- `data-fetcher` - Fetch historical data for optimization

---

**Version**: 1.0.0
**Last Updated**: 2026-03-19
**Maintained By**: Trading Team
