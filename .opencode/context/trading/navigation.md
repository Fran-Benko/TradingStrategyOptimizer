# Trading Context Navigation

**Purpose**: Navigate trading-specific context files  
**Last Updated**: 2026-03-19

---

## Quick Access

### Standards (Critical - Load First)
| File | Purpose | When to Load |
|------|---------|--------------|
| [trading-patterns.md](standards/trading-patterns.md) | Trading strategy patterns | Designing strategies |
| [risk-management.md](standards/risk-management.md) | Risk management principles | All trading tasks |
| [backtesting-standards.md](standards/backtesting-standards.md) | Backtesting best practices | Running backtests |
| [market-data-integration.md](standards/market-data-integration.md) | Data source integration | Fetching market data |

### Concepts
| File | Purpose |
|------|---------|
| [strategy-types.md](concepts/strategy-types.md) | Types of trading strategies |
| [backtesting-fundamentals.md](concepts/backtesting-fundamentals.md) | Backtesting basics |
| [risk-metrics.md](concepts/risk-metrics.md) | Understanding risk metrics |

### Examples
| File | Purpose |
|------|---------|
| [momentum-strategy-example.md](examples/momentum-strategy-example.md) | Momentum strategy implementation |
| [mean-reversion-example.md](examples/mean-reversion-example.md) | Mean reversion strategy |
| [ml-strategy-example.md](examples/ml-strategy-example.md) | ML-based strategy |

### Guides
| File | Purpose |
|------|---------|
| [creating-new-strategy.md](guides/creating-new-strategy.md) | How to create a strategy |
| [running-backtest.md](guides/running-backtest.md) | How to run backtests |
| [optimizing-parameters.md](guides/optimizing-parameters.md) | Parameter optimization |

### Lookup (Quick Reference)
| File | Purpose |
|------|---------|
| [backtrader-commands.md](lookup/backtrader-commands.md) | Backtrader API reference |
| [data-sources-apis.md](lookup/data-sources-apis.md) | Data source APIs |
| [metrics-reference.md](lookup/metrics-reference.md) | Metrics formulas |

### Errors (Common Issues)
| File | Purpose |
|------|---------|
| [data-fetching-errors.md](errors/data-fetching-errors.md) | Data fetching issues |
| [backtest-errors.md](errors/backtest-errors.md) | Backtesting errors |
| [optimization-errors.md](errors/optimization-errors.md) | Optimization problems |

---

## Context Loading Patterns

### For Strategy Development
```
Load:
1. standards/trading-patterns.md
2. standards/risk-management.md
3. examples/[relevant-strategy-type]-example.md
4. guides/creating-new-strategy.md
```

### For Data Integration
```
Load:
1. standards/market-data-integration.md
2. lookup/data-sources-apis.md
3. errors/data-fetching-errors.md
```

### For Backtesting
```
Load:
1. standards/backtesting-standards.md
2. standards/risk-management.md
3. guides/running-backtest.md
4. lookup/metrics-reference.md
```

---

## Related Context

- [Development Standards](../development/standards/python-standards.md)
- [Testing Standards](../development/standards/testing-standards.md)
- [System Architecture](../development/architecture/system-design.md)

---

**Version**: 1.0.0