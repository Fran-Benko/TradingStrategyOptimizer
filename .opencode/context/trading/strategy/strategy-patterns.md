# Strategy Patterns

## Descripción

Patrones de diseño para estrategias de tradingalgorítmico.

## Patrones Principales

### 1. Momentum Strategy

```python
class MomentumStrategy(BaseStrategy):
    """
    Estrategia basada en momentum.
    
    Principio: "The trend is your friend"
    Compra cuando el precio sube, vende cuando baja.
    """
    
    def __init__(self, period: int = 20, threshold: float = 0.02):
        self.period = period
        self.threshold = threshold
    
    def generate_signals(self, data: pd.DataFrame) -> np.ndarray:
        close = data["close"]
        returns = close.pct_change(self.period)
        
        signals = np.where(returns > self.threshold, 1,  # Strong uptrend
                  np.where(returns < -self.threshold, -1, 0))  # Strong downtrend
        
        return signals
```

### 2. Mean Reversion Strategy

```python
class MeanReversionStrategy(BaseStrategy):
    """
    Estrategia de reversión a la media.
    
    Principio: "Precios extremes vuelven a la media"
    Compra cuando está bajo, vende cuando está alto.
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: pd.DataFrame) -> np.ndarray:
        close = data["close"]
        sma = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()
        
        z_score = (close - sma) / std
        
        signals = np.where(z_score < -self.std_dev, 1,   # Oversold
                 np.where(z_score > self.std_dev, -1, 0))  # Overbought
        
        return signals
```

### 3. Breakout Strategy

```python
class BreakoutStrategy(BaseStrategy):
    """
    Estrategia de ruptura de rangos.
    
    Principio: "Rupturas de rangos generan movimientos"
    Compra en ruptura de máximos, vende en ruptura de mínimos.
    """
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
    
    def generate_signals(self, data: pd.DataFrame) -> np.ndarray:
        high = data["high"]
        low = data["low"]
        
        highest_high = high.rolling(self.lookback).max().shift(1)
        lowest_low = low.rolling(self.lookback).min().shift(1)
        
        close = data["close"]
        
        signals = np.where(close > highest_high, 1,
                 np.where(close < lowest_low, -1, 0))
        
        return signals
```

## Indicadores Comunes

| Indicador | Tipo | Uso |
|-----------|------|-----|
| RSI | Oscilador | Sobrecompra/sobreventa |
| MACD | Tendencia | Crossover signals |
| Bollinger Bands | Volatilidad | Mean reversion |
| ATR | Volatilidad | Stop loss |
| ADX | Tendencia | Fuerza de tendencia |

## Combinación de Estrategias

```python
class CompositeStrategy:
    """
    Combina múltiples estrategias con votación.
    """
    
    def __init__(self, strategies: list, weights: list = None):
        self.strategies = strategies
        self.weights = weights or [1] * len(strategies)
    
    def generate_signals(self, data: pd.DataFrame) -> np.ndarray:
        weighted_signals = np.zeros(len(data))
        
        for strategy, weight in zip(self.strategies, self.weights):
            signals = strategy.generate_signals(data)
            weighted_signals += signals * weight
        
        # Normalize: majority vote
        return np.sign(weighted_signals)
```

## Best Practices

1. **Validación**: Siempre validar con datos out-of-sample
2. **Parámetros**: Evitar overfitting con parámetros optimizados
3. **Costos**: Incluir comisiones y slippage en backtests
4. **Risk Management**: Nunca arriesgar más del 2% por trade
5. **Diversificación**: Combinar estrategias no correlacionadas

---

**Última actualización**: 2026-03-19
