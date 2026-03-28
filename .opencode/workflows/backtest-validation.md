---
name: backtest-validation
description: Comprehensive backtest validation and robustness testing workflow
triggers:
  - Strategy backtest completion
  - Pre-production validation
  - Strategy parameter changes
  - Walk-forward analysis
required_skills:
  - verification-before-completion
  - systematic-debugging
---

# Backtest Validation Workflow

## Descripción

Workflow completo para validar resultados de backtest, verificar métricas y asegurar robustez antes de deployment.

## Pasos

### 1. Ejecución de Backtest

**Skill requerido:** `verification-before-completion`

```
@MetricsAnalyst ejecuta backtest
Incluye: configuración, datos, símbolos
```

**Configuración de backtest:**

```python
from trading_system.backtesting.engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestResult
)
from trading_system.strategies.momentum.rsi_strategy import (
    RSIStrategy,
    RSIStrategyConfig
)

# Configurar backtest
config = BacktestConfig(
    initial_capital=100_000,
    commission=0.001,          # 0.1% por trade
    slippage=0.0005,           # 0.05% slippage
    margin_rate=1.0,           # Sin leverage
    position_sizing=0.95       # Usar 95% del capital
)

# Crear estrategia
strategy_config = RSIStrategyConfig(
    period=14,
    overbought=70,
    oversold=30
)
strategy = RSIStrategy(strategy_config)

# Ejecutar
engine = BacktestEngine(config)
result = engine.run(strategy, data, symbol="AAPL")

print(result.summary())
```

**Parámetros de backtest:**
| Parámetro | Valor Recomendado | Justificación |
|-----------|-------------------|----------------|
| Commission | 0.1% - 0.2% | Broker realista |
| Slippage | 0.05% - 0.1% | Entry/exit realista |
| Initial Capital | Depende de strategy | Capital mínimo |
| Position Sizing | 90% - 100% | Evitar cash drag |

### 2. Verificación de Métricas

**Métricas críticas a verificar:**

```python
# Extraer métricas del resultado
print(f"""
=== Backtest Results ===
Total Return:     {result.total_return:.2%}
Sharpe Ratio:     {result.sharpe_ratio:.4f}
Sortino Ratio:    {result.sortino_ratio:.4f}
Max Drawdown:     {result.max_drawdown_pct:.2%}
Win Rate:         {result.win_rate:.2%}
Profit Factor:    {result.profit_factor:.4f}
Total Trades:     {result.total_trades}
Avg Trade:        {result.avg_trade_pct:.4f}
Calmar Ratio:     {result.calmar_ratio:.4f}
""")
```

**Umbrales de aceptación:**

| Métrica | Mínimo | Ideal | Crítico |
|---------|--------|-------|---------|
| Sharpe Ratio | 0.5 | 1.0+ | < 0.3 |
| Max Drawdown | < 25% | < 15% | > 35% |
| Win Rate | > 40% | > 50% | < 35% |
| Profit Factor | > 1.0 | > 1.3 | < 0.9 |
| Total Trades | > 30 | > 100 | < 20 |

**Checklist de métricas:**
- [ ] Sharpe ≥ 0.5
- [ ] Max Drawdown < 25%
- [ ] Win Rate > 40%
- [ ] Profit Factor > 1.0
- [ ] Suficientes trades para significancia estadística

### 3. Walk-Forward Validation

**Skill requerido:** `systematic-debugging`

**Implementación con walk-forward:**

```python
from trading_system.optimization.walk_forward import (
    WalkForwardOptimizer,
    WalkForwardConfig,
    WindowType,
    walk_forward_analysis
)
from trading_system.optimization.optimizer import MetricType

# Configurar walk-forward
wf_config = WalkForwardConfig(
    window_type=WindowType.ROLLING,  # o EXPANDING
    train_window=252,                # ~1 año training
    test_window=63,                  # ~1 trimestre testing
    min_train_periods=126,           # Mínimo 6 meses
    min_test_periods=20,             # Mínimo 1 mes
    min_trades_per_period=5,        # Mínimo 5 trades
    optimization_metric=MetricType.SHARPE_RATIO
)

# Crear optimizer
wf_optimizer = WalkForwardOptimizer(
    backtest_config=config,
    walk_forward_config=wf_config
)

# Definir grid de parámetros
param_grid = {
    'period': [10, 14, 20],
    'overbought': [65, 70, 75],
    'oversold': [25, 30, 35]
}

# Ejecutar
wf_result = wf_optimizer.optimize(
    strategy_class=RSIStrategy,
    data=data,
    param_grid=param_grid,
    symbol="AAPL"
)

print(wf_result.summary())
print(f"Robustness Score: {wf_result.robustness_score:.4f}")
```

**Interpretación de resultados:**

```python
# Analizar resultados
print(f"""
=== Walk-Forward Analysis ===
Stability Score:      {wf_result.stability_score:.4f}
Walk-Forward Return:  {wf_result.walk_forward_return:.2%}
Degradation Ratio:    {wf_result.degradation_ratio:.4f}
Robustness Score:     {wf_result.robustness_score:.4f}

Valid Periods:        {len(wf_result.get_valid_periods())}/{wf_result.total_periods}
Best Params:          {wf_result.get_robust_params()}
""")
```

**Criterios de robustez:**

| Métrica | Aceptable | Excelente |
|---------|-----------|-----------|
| Stability Score | > 0.4 | > 0.6 |
| Degradation Ratio | > 0.5 | > 0.7 |
| Robustness Score | > 0.4 | > 0.6 |
| Valid Periods | > 60% | > 80% |

### 4. Pruebas de Robustez

**Sensitivity Analysis:**

```python
# Probar variaciones de parámetros
from trading_system.optimization.optimizer import StrategyOptimizer

param_grid = {
    'period': range(10, 30, 2),
    'overbought': range(60, 80, 5),
    'oversold': range(20, 40, 5)
}

optimizer = StrategyOptimizer(
    backtest_config=config,
    optimization_config=OptimizationConfig(
        n_trials=100,
        metric=MetricType.SHARPE_RATIO
    )
)

result = optimizer.optimize(
    strategy_class=RSIStrategy,
    data=data,
    param_grid=param_grid,
    symbol="AAPL"
)

print(f"Best params: {result.best_params}")
print(f"Best score: {result.best_score:.4f}")
```

**Robustness checks:**

- [ ] Parameter sensitivity within acceptable range
- [ ] Consistent performance across different time periods
- [ ] No overfitting to specific market conditions
- [ ] Graceful degradation with parameter changes

### 5. Reporte de Validación

**Generar reporte estructurado:**

```python
# Generar DataFrame de resultados
results_df = wf_result.to_dataframe()
results_df.to_csv("walk_forward_results.csv", index=False)

# Generar visualización
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# In-sample vs Out-of-sample returns
axes[0, 0].plot(results_df['period'], results_df['is_return'], label='In-Sample')
axes[0, 0].plot(results_df['period'], results_df['os_return'], label='Out-of-Sample')
axes[0, 0].set_title('Returns: IS vs OOS')
axes[0, 0].legend()

# Sharpe ratio comparison
axes[0, 1].plot(results_df['period'], results_df['is_sharpe'], label='IS Sharpe')
axes[0, 1].plot(results_df['period'], results_df['os_sharpe'], label='OOS Sharpe')
axes[0, 1].set_title('Sharpe Ratio: IS vs OOS')
axes[0, 1].legend()

# Degradation ratio
axes[1, 0].plot(results_df['period'], results_df['degradation'])
axes[1, 0].axhline(y=0.5, color='r', linestyle='--', label='Acceptable')
axes[1, 0].set_title('Degradation Ratio')

# Trade count per period
axes[1, 1].bar(results_df['period'], results_df['trade_count'])
axes[1, 1].set_title('Trade Count per Period')

plt.tight_layout()
plt.savefig("backtest_validation_report.png", dpi=150)
```

**Checklist de reporte:**
- [ ] Resumen ejecutivo
- [ ] Métricas clave
- [ ] Walk-forward results
- [ ] Visualizaciones
- [ ] Recomendación go/no-go

### 6. Decision Matrix

**Decision framework:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    BACKTEST VALIDATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  METRICS    │    │   WALK-     │    │  SENSITIVITY│        │
│  │  CHECK      │───▶│  FORWARD    │───▶│  CHECK      │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│        │                  │                  │                 │
│        ▼                  ▼                  ▼                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              COMPOSITE SCORE                        │       │
│  │         (Metrics 40% + WF 40% + Sensitivity 20%)   │       │
│  └─────────────────────────────────────────────────────┘       │
│                          │                                     │
│         ┌────────────────┼────────────────┐                    │
│         ▼                ▼                ▼                    │
│   ┌──────────┐    ┌──────────────┐   ┌──────────┐           │
│   │  GO       │    │  CONDITIONAL │   │  NO-GO   │           │
│   │  > 0.70   │    │  0.50-0.70   │   │  < 0.50  │           │
│   └──────────┘    └──────────────┘   └──────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Decision criteria:**

| Score | Decision | Action |
|-------|----------|--------|
| ≥ 0.70 | **GO** | Proceder a paper trading |
| 0.50 - 0.70 | **CONDITIONAL** | Revisar parámetros, más validación |
| < 0.50 | **NO-GO** | No proceeder, investigar causa |

## Integración con Agentes

| Paso | Agente Principal | Agentes de Soporte |
|------|-----------------|-------------------|
| Execution | @MetricsAnalyst | @StrategyDesigner |
| Metrics Verification | @MetricsAnalyst | - |
| Walk-Forward | @MetricsAnalyst | @StrategyDesigner |
| Robustness | @MetricsAnalyst | @PythonDeveloper |
| Reporting | @MetricsAnalyst | @DocWriter |

## Módulos de Referencia

- **Backtest Engine:** `src/trading_system/backtesting/engine.py`
- **Walk-Forward:** `src/trading_system/optimization/walk_forward.py`
- **Optimizer:** `src/trading_system/optimization/optimizer.py`
- **Metrics:** `src/trading_system/metrics/`
- **Results:** `src/trading_system/backtesting/results.py`

## Comandos Útiles

```bash
# Ejecutar backtest rápido
python -c "
from src.trading_system.backtesting.engine import BacktestEngine
from src.trading_system.strategies.momentum.rsi_strategy import RSIStrategy
# ... setup ...
print(engine.run(strategy, data, 'AAPL').summary())
"

# Generar walk-forward
python -c "
from src.trading_system.optimization.walk_forward import walk_forward_analysis
from src.trading_system.strategies.momentum.rsi_strategy import RSIStrategy
# ... setup ...
result = walk_forward_analysis(RSIStrategy, data, param_grid)
print(result.summary())
"
```

---

**Última actualización**: 2026-03-19
