---
name: risk-analyzer
description: Use when analyzing portfolio risk, calculating position sizing, VaR, or performing correlation analysis for risk management.
---

# Risk Analyzer Skill

This skill provides comprehensive risk analysis capabilities for trading portfolios, including position sizing, Value at Risk (VaR) calculations, correlation analysis, and portfolio-level risk metrics.

## When to Use This Skill

- Calculating position sizes for trades
- Analyzing portfolio-level risk exposure
- Computing Value at Risk (VaR) and Expected Shortfall
- Correlation analysis for diversification
- Risk decomposition across positions
- Stress testing portfolio scenarios
- Rebalancing recommendations

## What This Skill Does

1. **Position Sizing**: Kelly criterion, fixed fraction, ATR-based
2. **VaR Calculations**: Historical, parametric, Monte Carlo
3. **Correlation Analysis**: Cross-asset correlations
4. **Risk Decomposition**: Factor and position attribution
5. **Stress Testing**: Historical and hypothetical scenarios
6. **Portfolio Optimization**: Risk-adjusted position allocation
7. **Risk Monitoring**: Real-time risk tracking

## How to Use

### Position Sizing
```
Calculate position size for AAPL trade
Entry: $150, Stop: $145, Account: $100,000
Risk per trade: 2%
```

### Portfolio Risk Analysis
```
Analyze risk for this multi-position portfolio
Show VaR, correlation, and position attribution
```

### Correlation Analysis
```
Analyze correlations between AAPL, GOOGL, MSFT, SPY
Calculate rolling correlations
```

### Stress Testing
```
Run stress test on portfolio for 2008-like scenario
Include: -40% equity, +3% VIX, -20% bonds
```

## Position Sizing Methods

### Kelly Criterion

```
Position Size = (Win Rate × Avg Win - Loss Rate × Avg Loss) / Avg Win
```

| Kelly Fraction | Description | Risk Level |
|----------------|-------------|------------|
| Full Kelly | Theoretical optimal | High volatility |
| Half Kelly | 50% of full | Moderate |
| Quarter Kelly | 25% of full | Conservative |

### Fixed Fraction

```
Position = (Account × Risk %) / (Entry - Stop)
```

### ATR-Based Sizing

```
Position = (Account × Risk %) / (ATR × Multiplier)
```

## Position Sizing Examples

### Example 1: Dollar Risk Sizing

**User**: "Calculate position size with $100,000 account, 2% risk"

**Output**:
```
=== Position Sizing Calculation ===

Account Size: $100,000
Risk Per Trade: 2% ($2,000)
Entry Price: $150.00
Stop Loss: $145.00
Risk per Share: $5.00

Position Size:
  Max Shares: 400 shares
  Position Value: $60,000
  Position %: 60% of account
  
  At Stop Loss:
    Loss: $2,000 (2.0%) ✓
    Remaining: $98,000
```

### Example 2: ATR-Based Sizing

**User**: "Size position using 20-day ATR for volatility adjustment"

**Output**:
```
=== ATR-Based Position Sizing ===

Symbol: AAPL
Current ATR (20): $3.25
ATR Multiplier: 2.0

Account: $100,000
Risk %: 1% ($1,000)
Risk per Share: $3.25 × 2 = $6.50

Position Size:
  Shares: 153
  Position Value: $22,950
  Position %: 23%
  
Volatility-Adjusted:
  Volatility (ATR): $3.25
  Expected Range: ±6.5%
```

### Example 3: Kelly Criterion

**User**: "Calculate Kelly-optimal position size"

**Output**:
```
=== Kelly Criterion Position Sizing ===

Historical Statistics:
  Win Rate: 58%
  Avg Win: $420
  Avg Loss: $185
  
Kelly Calculation:
  W = 0.58 (win rate)
  R = 2.27 (avg win / avg loss)
  Kelly % = W - (1-W)/R
  Kelly % = 0.58 - 0.42/2.27
  Kelly % = 0.395 (39.5%)

Position Recommendations:
  Full Kelly: 39.5% ($39,500) - HIGH RISK
  Half Kelly: 19.8% ($19,800) - MODERATE
  Quarter Kelly: 9.9% ($9,900) - CONSERVATIVE

Recommended: Half Kelly for sustainable trading
```

## Value at Risk (VaR)

### VaR Types

| Method | Description | Pros | Cons |
|--------|-------------|------|------|
| Historical | Uses actual returns | Simple | Assumes past = future |
| Parametric | Assumes normal distribution | Fast | Sensitive to outliers |
| Monte Carlo | Simulations | Flexible | Computationally heavy |
| Cornish-Fisher | Adjusted for skew/kurtosis | Accurate | Complex |

### VaR Calculation

```
Historical VaR (95%):
  VaR = Percentile(returns, 5%)
  VaR = -2.3% (5% chance of losing > 2.3%)

Parametric VaR (95%):
  VaR = Mean - (1.65 × StdDev)
  VaR = 0.5% - (1.65 × 1.8%)
  VaR = -2.47%
```

### Expected Shortfall (CVaR)

```
CVaR = Average of returns beyond VaR
CVaR = -3.8% (average loss when in worst 5%)
```

## Portfolio Risk Analysis

### Risk Metrics Dashboard

```
=== Portfolio Risk Summary ===

Portfolio Value: $500,000
Daily VaR (95%): -$12,500 (-2.5%)
Weekly VaR (95%): -$28,750 (-5.75%)
Monthly VaR (95%): -$62,500 (-12.5%)

Expected Shortfall (CVaR 95%):
  Daily: -$18,750 (-3.75%)
  Weekly: -$43,125 (-8.63%)
  Monthly: -$87,500 (-17.5%)

Risk Contribution by Position:
  AAPL: 35% of risk
  GOOGL: 25% of risk
  MSFT: 20% of risk
  SPY: 15% of risk
  Cash: 5% of risk
```

### Position Risk Attribution

```
=== Risk Attribution ===

Portfolio: $500,000 | VaR: $12,500

Position    Value     Weight   Marginal VaR  Component VaR
------------------------------------------------------------
AAPL       $175,000    35%       2.8%          $4,375
GOOGL      $125,000    25%       2.5%          $3,125
MSFT       $100,000    20%       2.2%          $2,200
SPY        $75,000     15%       1.9%          $1,425
Cash       $25,000      5%       0.0%          $0
------------------------------------------------------------
```

## Correlation Analysis

### Correlation Matrix

```
=== Correlation Matrix (60-day rolling) ===

        AAPL    GOOGL    MSFT     SPY      VIX
AAPL    1.00    0.72     0.85     0.88    -0.45
GOOGL   0.72    1.00     0.78     0.75    -0.38
MSFT    0.85    0.78     1.00     0.82    -0.42
SPY     0.88    0.75     0.82     1.00    -0.52
VIX    -0.45   -0.38    -0.42    -0.52     1.00

Diversification Benefit:
  Average Correlation: 0.71
  Portfolio Diversification Ratio: 0.65
```

### Rolling Correlation

```
=== Rolling Correlation Analysis ===

AAPL-SPY 60-day Rolling:
  Current: 0.88
  Average: 0.82
  Min: 0.65
  Max: 0.95
  
  High correlation suggests limited diversification benefit
  Consider reducing SPY exposure or adding uncorrelated assets
```

### Diversification Recommendations

```
Correlation Analysis:
  High Correlations (>0.8):
    AAPL-MSFT: 0.85 - High redundancy
    AAPL-SP500: 0.88 - High beta
    
  Moderate Correlations (0.5-0.8):
    GOOGL-MSFT: 0.78 - Some diversification
    
  Low/Negative Correlations (<0.5):
    SPY-VIX: -0.52 - Good hedge
    AAPL-VIX: -0.45 - Good hedge

Recommendations:
  1. Consider reducing AAPL-SP500 overlap
  2. Add VIX or inverse ETF for hedging
  3. Add low-correlation assets (bonds, commodities)
```

## Stress Testing

### Historical Scenarios

```
=== Stress Test Results ===

Scenario: 2008 Financial Crisis
  Equity Drawdown: -40%
  VIX Spike: +150%
  Bond Rally: +10%

Portfolio Impact:
  Estimated Loss: -28.5%
  Recovery Time: 18 months

Current Allocation: $500,000 → $357,500

Mitigation:
  Add 10% allocation to inverse S&P
  Reduce equity exposure to 60%
  Expected loss reduction: -8%
```

### Hypothetical Scenarios

```
=== Hypothetical Stress Test ===

Scenario: Flash Crash
  Market drops 10% in 1 hour
  Recovers 50% within day
  High volatility spike

Impact Analysis:
  Intraday Loss: -$50,000 (-10%)
  End of Day: -$25,000 (-5%)
  Stop Losses: Would trigger
  
Risk Mitigation:
  Use wider stops during high volatility
  Reduce position sizes by 50%
  Pre-set limit orders for exit
```

## Risk Limits and Alerts

### Portfolio Risk Limits

```
=== Risk Limits Configuration ===

Capital Risk:
  Max Daily Loss: 3% ($15,000)
  Max Weekly Loss: 7% ($35,000)
  Max Monthly Loss: 15% ($75,000)
  
Position Risk:
  Max Position Size: 25% ($125,000)
  Max Sector Exposure: 40% ($200,000)
  Max Single Trade Risk: 2% ($10,000)

Margin Risk:
  Max Margin Utilization: 50%
  Max Leverage: 2x
```

### Alert Thresholds

```
=== Risk Alerts ===

Current Risk Status: MODERATE

Active Alerts:
  ⚠️ Daily VaR at 85% of limit
  ⚠️ Sector concentration at 38% (limit: 40%)
  
Recommended Actions:
  1. Reduce AAPL position by 5%
  2. Wait for VIX to normalize before adding
  3. Monitor correlation changes
```

## Output Format

### Complete Risk Report

```
=== Portfolio Risk Analysis ===

Portfolio Value: $500,000
Positions: 4
Risk Free Rate: 4.5%

VALUE AT RISK
  Daily VaR (95%): -$12,500 (-2.5%)
  Weekly VaR (95%): -$28,750 (-5.75%)
  Monthly VaR (95%): -$62,500 (-12.5%)
  
EXPECTED SHORTFALL
  Daily CVaR (95%): -$18,750 (-3.75%)
  
POSITION RISK
  Largest Position: AAPL 35%
  Highest Marginal VaR: AAPL 2.8%
  
CORRELATION METRICS
  Avg Pairwise Correlation: 0.71
  Diversification Ratio: 0.65
  
STRESS TEST
  2008 Scenario Loss: -28.5%
  COVID Scenario Loss: -18.2%
  Flash Crash Loss: -10%
  
RISK SCORE: 6.5/10 (Moderate Risk)
```

## Examples

### Example 1: Multi-Position Analysis

**User**: "Analyze risk for my portfolio: AAPL 35%, GOOGL 25%, MSFT 20%, SPY 15%, Cash 5%"

**Output**:
```
=== Multi-Position Risk Analysis ===

Portfolio: $500,000

VaR Analysis:
  Daily VaR (95%): $12,500 (2.5%)
  CVaR (95%): $18,750 (3.75%)

Position Risk:
  AAPL: $175,000 (35%) - Marginal VaR: 2.8%
  GOOGL: $125,000 (25%) - Marginal VaR: 2.5%
  MSFT: $100,000 (20%) - Marginal VaR: 2.2%
  SPY: $75,000 (15%) - Marginal VaR: 1.9%
  Cash: $25,000 (5%) - Marginal VaR: 0%

Concentration Risk:
  Equity Concentration: 95% (HIGH)
  Sector Concentration: Tech 80% (VERY HIGH)
  
Recommendations:
  1. Reduce AAPL/SPY overlap
  2. Add sector diversification
  3. Consider bonds for risk reduction
```

### Example 2: Rebalancing Analysis

**User**: "What rebalancing actions would reduce portfolio risk?"

**Output**:
```
=== Rebalancing Recommendations ===

Current vs Target Allocation:

Current:                  Target:
AAPL: 35% → Reduce to 25%
GOOGL: 25% → Maintain
MSFT: 20% → Maintain  
SPY: 15% → Increase to 20%
Bonds: 0% → Add 10%

Expected Impact:
  Risk Reduction: -15%
  Correlation Decrease: -0.08
  Diversification Increase: +12%
  
Action Plan:
  1. Sell $50,000 AAPL
  2. Buy $25,000 SPY
  3. Buy $50,000 bonds
  4. Distribute gains to underweight positions
```

## Technical Details

**Implementation**: Custom risk analysis functions

**Key Calculations**:
- Position Size: (Account × Risk %) / Risk per Share
- VaR: Percentile/Parametric/Monte Carlo methods
- CVaR: Mean of returns beyond VaR threshold
- Correlation: Pearson/Spearman rolling correlations
- Kelly: W - (1-W)/R formula

**Dependencies**: pandas, numpy, scipy

**Usage**:
```python
# Position sizing
risk_per_trade = account * 0.02
shares = risk_per_trade / (entry - stop)

# VaR calculation
var_95 = returns.quantile(0.05)
cvar_95 = returns[returns <= var_95].mean()

# Correlation
corr_matrix = returns.corr()
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Over-concentration | Diversify across sectors/assets |
| Ignoring correlations | Account for correlation in VaR |
| Using past VaR only | Use multiple VaR methods |
| Ignoring tail risk | Include CVaR in analysis |
| Under-sizing stops | Use proper position sizing |

## Tips

- Diversify across uncorrelated assets
- Use multiple VaR methods for robustness
- Monitor correlation changes over time
- Include stress tests in risk analysis
- Set appropriate risk limits
- Rebalance periodically
- Account for tail risks (CVaR)
- Consider margin and leverage limits

## Related Skills

- `metrics-calculator` - Calculate detailed metrics
- `backtest-runner` - Run backtests with risk controls
- `strategy-optimizer` - Optimize for risk-adjusted returns

---

**Version**: 1.0.0
**Last Updated**: 2026-03-19
**Maintained By**: Trading Team
