# Refactor Helper Skill

## Descripción

Ayuda con tareas de refactoring de código Python. Proporciona guías, patrones y automatización para mejorar la calidad del código existente.

## Activación

```
Refactoriza [módulo o código]
```

## Patrones de Refactoring

### 1. Extract Method

**Antes:**
```python
def process_order(order):
    # Validar orden
    if not order.symbol:
        raise ValueError("Symbol required")
    if order.quantity <= 0:
        raise ValueError("Quantity must be positive")
    if order.price <= 0:
        raise ValueError("Price must be positive")
    
    # Calcular costo
    cost = order.quantity * order.price
    commission = cost * 0.001
    
    # Ejecutar orden
    execute_order(order)
    
    return {"status": "success", "cost": cost, "commission": commission}
```

**Después:**
```python
def process_order(order: Order) -> dict:
    """Process a trading order."""
    self._validate_order(order)
    cost, commission = self._calculate_costs(order)
    self._execute_order(order)
    return self._build_response(cost, commission)

def _validate_order(self, order: Order) -> None:
    """Validate order parameters."""
    if not order.symbol:
        raise ValueError("Symbol required")
    if order.quantity <= 0:
        raise ValueError("Quantity must be positive")
    if order.price <= 0:
        raise ValueError("Price must be positive")

def _calculate_costs(self, order: Order) -> tuple:
    """Calculate order costs."""
    cost = order.quantity * order.price
    commission = cost * 0.001
    return cost, commission

def _execute_order(self, order: Order) -> None:
    """Execute the order."""
    execute_order(order)

def _build_response(self, cost: float, commission: float) -> dict:
    """Build success response."""
    return {"status": "success", "cost": cost, "commission": commission}
```

### 2. Replace Conditional with Polymorphism

**Antes:**
```python
class DataFetcher:
    def fetch(self, source: str, symbol: str):
        if source == "yahoo":
            return self._fetch_yahoo(symbol)
        elif source == "alpaca":
            return self._fetch_alpaca(symbol)
        elif source == "google":
            return self._fetch_google(symbol)
        else:
            raise ValueError(f"Unknown source: {source}")
```

**Después:**
```python
from abc import ABC, abstractmethod

class DataFetcher(ABC):
    @abstractmethod
    def fetch(self, symbol: str) -> pd.DataFrame:
        pass

class YahooFetcher(DataFetcher):
    def fetch(self, symbol: str) -> pd.DataFrame:
        # Yahoo-specific implementation
        pass

class AlpacaFetcher(DataFetcher):
    def fetch(self, symbol: str) -> pd.DataFrame:
        # Alpaca-specific implementation
        pass

class FetcherFactory:
    @staticmethod
    def create(source: str) -> DataFetcher:
        fetchers = {
            "yahoo": YahooFetcher,
            "alpaca": AlpacaFetcher,
        }
        if source not in fetchers:
            raise ValueError(f"Unknown source: {source}")
        return fetchers[source]()
```

### 3. Introduce Parameter Object

**Antes:**
```python
def backtest(
    strategy_name: str,
    symbol: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
    commission: float,
    slippage: float
):
    # Backtest logic
    pass

# Usage
backtest("RSI", "AAPL", "2023-01-01", "2023-12-31", 100000, 0.001, 0.0005)
```

**Después:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    commission: float = 0.001
    slippage: float = 0.0005
    position_size: float = 1.0

@dataclass
class BacktestResult:
    """Results from backtesting."""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    trades: list

def backtest(config: BacktestConfig) -> BacktestResult:
    """Run backtest with configuration."""
    # Backtest logic
    pass

# Usage
config = BacktestConfig(
    strategy_name="RSI",
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2023-12-31"
)
result = backtest(config)
```

### 4. Replace Magic Numbers with Constants

**Antes:**
```python
def calculate_commission(cost: float) -> float:
    return cost * 0.001

def calculate_slippage(price: float) -> float:
    return price * 0.0005
```

**Después:**
```python
from typing import Final

COMMISSION_RATE: Final[float] = 0.001  # 0.1%
SLIPPAGE_RATE: Final[float] = 0.0005   # 0.05%
MAX_POSITION_SIZE: Final[float] = 0.95  # 95% of capital

def calculate_commission(cost: float) -> float:
    return cost * COMMISSION_RATE

def calculate_slippage(price: float) -> float:
    return price * SLIPPAGE_RATE
```

## Checklist de Refactoring

- [ ] Tests still passing after refactor
- [ ] No duplicate code introduced
- [ ] Type hints remain correct
- [ ] Docstrings updated si es necesario
- [ ] Performance no degradada
- [ ] Code review realizado

## Uso

### Refactorizar función

```
Refactoriza calculate_risk en src/trading_system/utils/risk.py
Patrón: extract method, introduce constants
```

### Mejorar estructura de clase

```
Refactoriza DataFetcher para usar Strategy Pattern
Agrega soporte para nuevos sources fácilmente
```

### Limpiar código heredado

```
Limpia código en src/trading_system/legacy/
Con: type hints, docstrings, remove dead code
```

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19
