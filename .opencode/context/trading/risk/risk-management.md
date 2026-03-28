# Risk Management

## Descripción

Patrones y prácticas para gestión de riesgos en trading algorítmico.

## Principios de Risk Management

### 1. Position Sizing

```python
def calculate_position_size(
    account_value: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float
) -> int:
    """
    Calcula tamaño de posición basado en riesgo.
    
    Args:
        account_value: Valor total de la cuenta
        risk_per_trade: Porcentaje de riesgo por trade (ej: 0.02 = 2%)
        entry_price: Precio de entrada
        stop_loss_price: Precio de stop loss
    
    Returns:
        Número de acciones a comprar
    """
    risk_amount = account_value * risk_per_trade
    risk_per_share = abs(entry_price - stop_loss_price)
    
    if risk_per_share == 0:
        return 0
    
    shares = int(risk_amount / risk_per_share)
    return max(1, shares)
```

### 2. Stop Loss Strategies

```python
class StopLossManager:
    """Gestor de stop loss."""
    
    @staticmethod
    def fixed_stop(entry_price: float, risk_pct: float) -> float:
        """Stop loss a porcentaje fijo."""
        return entry_price * (1 - risk_pct)
    
    @staticmethod
    def atr_stop(entry_price: float, atr: float, multiplier: float = 2.0) -> float:
        """Stop loss basado en ATR."""
        return entry_price - (atr * multiplier)
    
    @staticmethod
    def chandelier_exit(high: float, entry_price: float, atr: float, 
                        period: int = 22) -> float:
        """Chandelier Exit - stop损失的的最高点减去ATR"""
        highest_high = high.rolling(period).max().iloc[-1]
        return highest_high - (atr * 3)
```

### 3. Portfolio Risk Limits

```python
class PortfolioRiskManager:
    """Gestor de riesgos a nivel de portfolio."""
    
    def __init__(self, config: dict):
        self.max_position_size = config.get("max_position_size", 0.05)  # 5%
        self.max_sector_exposure = config.get("max_sector_exposure", 0.30)  # 30%
        self.max_correlation = config.get("max_correlation", 0.7)
        self.max_drawdown_limit = config.get("max_drawdown_limit", 0.20)  # 20%
    
    def check_position_limits(
        self, 
        new_position: float, 
        current_positions: dict,
        account_value: float
    ) -> bool:
        """Verifica si nueva posición está dentro de límites."""
        
        new_position_value = new_position * account_value
        
        # Check position size limit
        if new_position_value > self.max_position_size * account_value:
            return False
        
        # Check total exposure
        total_exposure = sum(current_positions.values()) + new_position
        if total_exposure > 1.0:
            return False
        
        return True
    
    def check_correlation(self, new_signal: str, positions: dict, 
                          correlations: dict) -> bool:
        """Verifica correlación con posiciones existentes."""
        
        for symbol, position in positions.items():
            corr = correlations.get((new_signal, symbol), 0)
            if corr > self.max_correlation:
                return False
        
        return True
```

### 4. Drawdown Management

```python
class DrawdownProtection:
    """Protección contra drawdowns excesivos."""
    
    def __init__(self, max_drawdown: float = 0.20):
        self.max_drawdown = max_drawdown
        self.peak_value = None
        self.trading_paused = False
    
    def check_drawdown(self, current_value: float) -> dict:
        """Evalúa drawdown actual y toma acciones."""
        
        if self.peak_value is None:
            self.peak_value = current_value
        
        if current_value > self.peak_value:
            self.peak_value = current_value
            self.trading_paused = False
        
        drawdown = (self.peak_value - current_value) / self.peak_value
        
        actions = {
            "current_drawdown": drawdown,
            "trading_paused": self.trading_paused,
            "action": None
        }
        
        # Trading holidays when drawdown exceeds limit
        if drawdown > self.max_drawdown and not self.trading_paused:
            self.trading_paused = True
            actions["action"] = "PAUSE_TRADING"
            actions["message"] = f"Trading paused: drawdown {drawdown:.1%} exceeds limit"
        
        # Resume trading when recovered
        if drawdown < self.max_drawdown * 0.5 and self.trading_paused:
            self.trading_paused = False
            actions["action"] = "RESUME_TRADING"
        
        return actions
```

### 5. Kelly Criterion

```python
def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calcula tamaño de posición óptimo según Kelly Criterion.
    
    Args:
        win_rate: Probabilidad de ganar (0 a 1)
        avg_win: Ganancia promedio en trades winners
        avg_loss: Pérdida promedio en trades losers
    
    Returns:
        Fracción óptima del capital a arriesgar (ej: 0.25 = 25%)
    """
    if avg_loss == 0:
        return 0
    
    win_loss_ratio = avg_win / avg_loss
    kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
    
    #建议使用Kelly的一半作为风险管理
    return max(0, kelly * 0.5)
```

## Risk Metrics

| Métrica | Descripción | Límite |
|---------|-------------|--------|
| VaR | Value at Risk al 95% | < 2% |
| CVaR | Expected shortfall | < 3% |
| Sharpe Ratio | Retorno ajustado por riesgo | > 1.0 |
| Sortino Ratio | Retorno vs downside | > 1.5 |
| Max Drawdown | Mayor caída desde peak | < 20% |
| Exposure | Porcentaje invertido | < 95% |

## Alertas de Riesgo

```python
class RiskAlerts:
    """Monitoreo de métricas de riesgo."""
    
    ALERTS = {
        "high_var": {"threshold": 0.02, "severity": "warning"},
        "large_drawdown": {"threshold": 0.15, "severity": "critical"},
        "high_correlation": {"threshold": 0.8, "severity": "warning"},
        "overexposure": {"threshold": 0.95, "severity": "critical"}
    }
    
    def check(self, metrics: dict) -> list:
        """Verifica métricas contra umbrales."""
        alerts = []
        
        for metric_name, config in self.ALERTS.items():
            value = metrics.get(metric_name, 0)
            if value > config["threshold"]:
                alerts.append({
                    "metric": metric_name,
                    "value": value,
                    "severity": config["severity"],
                    "threshold": config["threshold"]
                })
        
        return alerts
```

---

**Última actualización**: 2026-03-19
