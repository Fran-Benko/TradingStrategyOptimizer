---
name: strategy-development
description: Complete workflow for developing and validating trading strategies
triggers:
  - New strategy feature request
  - Strategy optimization iteration
  - Strategy refactoring
required_skills:
  - brainstorming
  - test-driven-development
  - verification-before-completion
---

# Strategy Development Workflow

## Descripción

Workflow completo para desarrollar estrategias de trading desde el diseño hasta la validación productiva.

## Pasos

### 1. Diseño de Estrategia

**Skill requerido:** `brainstorming`

```
@StrategyDesigner diseña estrategia de [tipo]
Incluye: indicadores, reglas de entrada/salida, gestión de riesgo
Referencia: src/trading_system/strategies/base/base.py
```

**Checklist de diseño:**
- [ ] Definir tipo de estrategia (momentum, mean reversion, arbitrage, ML-based)
- [ ] Identificar indicadores técnicos requeridos
- [ ] Diseñar reglas de entrada/salida
- [ ] Definir parámetros ajustables
- [ ] Diseñar gestión de posición y riesgo
- [ ] Documentar hipótesis de mercado

**Patrones de referencia:**
- Momentum: `src/trading_system/strategies/momentum/rsi_strategy.py`
- Mean Reversion: `src/trading_system/strategies/mean_reversion/bollinger_strategy.py`
- Arbitrage: `src/trading_system/strategies/arbitrage/pairs_trading_strategy.py`
- ML-Based: `src/trading_system/strategies/ml_based/momentum_ml_strategy.py`

### 2. Setup de Desarrollo

```bash
# Crear branch
git checkout -b strategy/[nombre-estrategia]

# Crear estructura de directorios
mkdir -p src/trading_system/strategies/[tipo]/
mkdir -p tests/unit/strategies/
mkdir -p tests/integration/strategies/

# Instalar dependencias
pip install -r requirements.txt
```

**Estructura de archivos:**
```
src/trading_system/strategies/[tipo]/
├── __init__.py
├── [nombre]_strategy.py      # Estrategia principal
├── indicators.py             # Indicadores custom (si aplica)
└── config.py                  # Configuración de parámetros

tests/
├── unit/strategies/
│   ├── test_[nombre]_strategy.py
│   └── test_[nombre]_config.py
└── integration/
    └── test_[nombre]_integration.py
```

### 3. Implementación

**Skill requerido:** `test-driven-development`

```
@StrategyDesigner implementa [componente]
Con: tests unitarios, validación de tipos
Referencia: src/trading_system/strategies/base/base.py
```

**Patrón base para estrategias:**

```python
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd

from trading_system.strategies.base.base import (
    BaseStrategy, 
    StrategyConfig,
    SignalType
)
from trading_system.strategies.indicators.momentum import calculate_rsi

@dataclass
class MyStrategyConfig(StrategyConfig):
    """Configuration for MyStrategy."""
    name: str = "MyStrategy"
    period: int = 14
    threshold: float = 0.5

    def validate(self) -> bool:
        if not 2 <= self.period <= 200:
            raise ValueError("Period must be between 2 and 200")
        return True

class MyStrategy(BaseStrategy):
    """My strategy description."""
    
    def __init__(self, config: Optional[MyStrategyConfig] = None):
        if config is None:
            config = MyStrategyConfig()
        config.validate()
        super().__init__(config)
        self.period = config.period

    @property
    def required_columns(self) -> List[str]:
        return ["close"]

    @property
    def min_periods(self) -> int:
        return self.period

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        # Implementar lógica de señales
        signals = np.zeros(len(data))
        # ... lógica ...
        return signals
```

**Patrón de commits:**
```
feat: add [tipo] [nombre] strategy
feat: implement [indicador] calculation
test: add unit tests for [nombre] strategy
docs: add docstrings for [nombre] strategy
refactor: extract [componente] to base class
```

### 4. Testing

```
@DataEngineer genera datos de prueba
@UnitTestEngineer genera tests para [estrategia]
@MetricsAnalyst valida métricas de backtest
```

**Tests requeridos:**
- [ ] Test de inicialización y configuración
- [ ] Test de validación de parámetros
- [ ] Test de señales con datos históricos
- [ ] Test de edge cases (datos insuficientes, NaN)
- [ ] Test de integración con BacktestEngine

```python
# Ejemplo de test
import pytest
import pandas as pd
import numpy as np

from trading_system.strategies.[tipo].[nombre]_strategy import (
    MyStrategy,
    MyStrategyConfig
)

class TestMyStrategy:
    def test_initialization(self):
        config = MyStrategyConfig(period=14)
        strategy = MyStrategy(config)
        assert strategy.period == 14

    def test_generate_signals(self):
        data = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100
        })
        strategy = MyStrategy()
        signals = strategy.generate_signals(data)
        assert len(signals) == len(data)
        assert set(signals).issubset({-1, 0, 1})
```

### 5. Backtesting Inicial

```
@MetricsAnalyst ejecuta backtest inicial
Incluye: Sharpe, Max Drawdown, Win Rate
```

**Métricas objetivo:**
- Sharpe Ratio ≥ 1.0
- Max Drawdown < 20%
- Win Rate > 45%
- Profit Factor > 1.2

```python
from trading_system.backtesting.engine import BacktestEngine, BacktestConfig

config = BacktestConfig(
    initial_capital=100000,
    commission=0.001
)
engine = BacktestEngine(config)
result = engine.run(strategy, data, "TEST")
print(result.summary())
```

### 6. Validación

```
@MetricsAnalyst valida robustez
@StrategyDesigner verifica walk-forward
```

**Checklist de validación:**
- [ ] Walk-forward analysis (usar `src/trading_system/optimization/walk_forward.py`)
- [ ] Sensitivity analysis de parámetros
- [ ] Validación en múltiples timeframes
- [ ] Backtesting con commission real

### 7. Documentación

**Documentar:**
- [ ] Docstrings completos (Google style)
- [ ] README con ejemplos de uso
- [ ] Diagrama de señales
- [ ] Hipótesis de mercado documentada

```python
class MyStrategy(BaseStrategy):
    """
    My Strategy Description.

    Esta estrategia implementa [descripción de la lógica].

    Args:
        config: Configuration object

    Attributes:
        period: Descripción del período

    Example:
        >>> config = MyStrategyConfig(period=14)
        >>> strategy = MyStrategy(config)
        >>> signals = strategy.generate_signals(data)
    """
```

### 8. Code Review

```
@CodeReviewer revisa strategy/[nombre]
@SecurityAuditor audita gestión de riesgo
```

**Checklist de PR:**
- [ ] Tests passing
- [ ] Coverage ≥ 80%
- [ ] Linting passing
- [ ] Documentación completa
- [ ] Walk-forward score ≥ 0.5

### 9. Merge

```bash
# Rebase on main
git rebase main

# Push y crear PR
git push origin strategy/[nombre]
gh pr create
```

## Integración con Agentes

| Paso | Agente Principal | Agentes de Soporte |
|------|-----------------|-------------------|
| Diseño | @StrategyDesigner | @TradingArchitect |
| Setup | @PythonDeveloper | - |
| Implement | @StrategyDesigner | @PythonDeveloper |
| Testing | @TestEngineer | @DataEngineer |
| Backtest | @MetricsAnalyst | @StrategyDesigner |
| Validation | @MetricsAnalyst | @StrategyDesigner |
| Documentation | @DocWriter | @StrategyDesigner |
| Review | @CodeReviewer | @SecurityAuditor |

## Módulos de Referencia

- **Base:** `src/trading_system/strategies/base/base.py`
- **Indicators:** `src/trading_system/strategies/indicators/`
- **Backtesting:** `src/trading_system/backtesting/`
- **Optimization:** `src/trading_system/optimization/`
- **Walk-Forward:** `src/trading_system/optimization/walk_forward.py`

---

**Última actualización**: 2026-03-19
