<!-- Context: trading/patterns | Priority: critical | Version: 1.0 | Updated: 2026-03-19 -->

# Trading Patterns Standards

**Purpose**: Design patterns and best practices for trading strategies  
**Priority**: CRITICAL - Load before designing strategies

---

## Core Principle

**All strategies MUST follow these patterns for consistency, testability, and maintainability.**

---

## Base Strategy Pattern

### Structure
```python
from abc import ABC, abstractmethod
import backtrader as bt

class BaseStrategy(bt.Strategy, ABC):
    """
    Abstract base for all strategies
    Enforces consistent interface
    """
    
    # Parameters with defaults
    params = (
        ('risk_per_trade', 0.02),
        ('stop_loss_pct', 0.05),
    )
    
    def __init__(self):
        self.order = None
        self.setup_indicators()
        self.setup_risk_management()
    
    @abstractmethod
    def setup_indicators(self):
        """Define technical indicators"""
        pass
    
    @abstractmethod
    def generate_signal(self) -> Optional[str]:
        """Return 'BUY', 'SELL', or None"""
        pass
    
    def next(self):
        """Called on each bar"""
        if self.order:
            return
        
        signal = self.generate_signal()
        if signal == 'BUY':
            self.execute_buy()
        elif signal == 'SELL':
            self.execute_sell()
```

**Why**: Consistent interface, enforced risk management, testable

---

## Strategy Types

### 1. Momentum Strategies

**Pattern**: Trend Following
```python
class MomentumStrategy(BaseStrategy):
    """
    Buy when momentum is positive
    Sell when momentum turns negative
    """
    
    def setup_indicators(self):
        self.sma_fast = bt.indicators.SMA(period=10)
        self.sma_slow = bt.indicators.SMA(period=30)
        self.crossover = bt.indicators.CrossOver(
            self.sma_fast, 
            self.sma_slow
        )
    
    def generate_signal(self):
        if self.crossover > 0:
            return 'BUY'
        elif self.crossover < 0:
            return 'SELL'
        return None
```

**Key Indicators**:
- Moving averages (SMA, EMA)
- RSI
- MACD
- ADX

**Best For**: Trending markets

---

### 2. Mean Reversion Strategies

**Pattern**: Buy Low, Sell High
```python
class MeanReversionStrategy(BaseStrategy):
    """
    Buy when price is oversold
    Sell when price is overbought
    """
    
    def setup_indicators(self):
        self.rsi = bt.indicators.RSI(period=14)
        self.bb = bt.indicators.BollingerBands(period=20)
    
    def generate_signal(self):
        if self.rsi < 30 and self.data.close < self.bb.bot:
            return 'BUY'
        elif self.rsi > 70 and self.data.close > self.bb.top:
            return 'SELL'
        return None
```

**Key Indicators**:
- RSI
- Bollinger Bands
- Z-score
- Standard deviation

**Best For**: Range-bound markets

---

### 3. Arbitrage Strategies

**Pattern**: Exploit Price Differences
```python
class PairsArbitrageStrategy(BaseStrategy):
    """
    Trade spread between correlated assets
    """
    
    def setup_indicators(self):
        self.spread = self.data0.close - self.data1.close
        self.spread_sma = bt.indicators.SMA(self.spread, period=20)
        self.spread_std = bt.indicators.StdDev(self.spread, period=20)
    
    def generate_signal(self):
        z_score = (self.spread - self.spread_sma) / self.spread_std
        
        if z_score < -2:
            return 'BUY'  # Buy spread
        elif z_score > 2:
            return 'SELL'  # Sell spread
        return None
```

**Key Metrics**:
- Spread
- Correlation
- Cointegration
- Z-score

**Best For**: Correlated assets

---

### 4. ML-Based Strategies

**Pattern**: Prediction-Based Trading
```python
class MLStrategy(BaseStrategy):
    """
    Use ML model for predictions
    """
    
    def __init__(self):
        super().__init__()
        self.model = self.load_model()
        self.features = []
    
    def setup_indicators(self):
        # Feature engineering
        self.sma = bt.indicators.SMA(period=20)
        self.rsi = bt.indicators.RSI(period=14)
        self.volume_sma = bt.indicators.SMA(
            self.data.volume, 
            period=20
        )
    
    def generate_signal(self):
        features = self.extract_features()
        prediction = self.model.predict([features])[0]
        
        if prediction > 0.6:
            return 'BUY'
        elif prediction < 0.4:
            return 'SELL'
        return None
    
    def extract_features(self):
        return [
            self.sma[0],
            self.rsi[0],
            self.data.volume[0] / self.volume_sma[0]
        ]
```

**Key Components**:
- Feature engineering
- Model training/validation
- Prediction threshold
- Model monitoring

**Best For**: Complex patterns

---

## Risk Management Patterns

### Position Sizing

**Fixed Fractional**:
```python
def calculate_position_size(self):
    account_value = self.broker.getvalue()
    risk_amount = account_value * self.params.risk_per_trade
    stop_distance = self.data.close[0] * self.params.stop_loss_pct
    return risk_amount / stop_distance
```

**Kelly Criterion**:
```python
def kelly_size(self, win_rate, avg_win, avg_loss):
    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    return max(0, min(kelly * 0.5, 0.25))  # Half Kelly, capped at 25%
```

### Stop Loss Patterns

**Fixed Percentage**:
```python
def set_stop_loss(self):
    stop_price = self.entry_price * (1 - self.params.stop_loss_pct)
    self.sell(exectype=bt.Order.Stop, price=stop_price)
```

**ATR-Based**:
```python
def set_atr_stop(self):
    atr = self.atr[0]
    stop_price = self.entry_price - (2 * atr)
    self.sell(exectype=bt.Order.Stop, price=stop_price)
```

**Trailing Stop**:
```python
def update_trailing_stop(self):
    if self.position:
        current_price = self.data.close[0]
        trail_amount = current_price * 0.05
        stop_price = current_price - trail_amount
        self.sell(exectype=bt.Order.StopTrail, trailamount=trail_amount)
```

---

## Testing Patterns

### Unit Testing
```python
def test_strategy_signal():
    """Test signal generation"""
    strategy = MomentumStrategy()
    strategy.sma_fast = [110]
    strategy.sma_slow = [100]
    
    signal = strategy.generate_signal()
    assert signal == 'BUY'
```

### Backtesting
```python
def backtest_strategy(strategy_class, data, params):
    """Standard backtest pattern"""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class, **params)
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.run()
    return cerebro.broker.getvalue()
```

---

## Anti-Patterns (Avoid)

### ❌ No Risk Management
```python
# BAD: No stop loss
def next(self):
    if self.signal:
        self.buy()  # Unlimited risk!
```

### ❌ Look-Ahead Bias
```python
# BAD: Using future data
def generate_signal(self):
    if self.data.close[1] > self.data.close[0]:  # Future data!
        return 'BUY'
```

### ❌ Overfitting
```python
# BAD: Too many parameters
params = (
    ('param1', 10),
    ('param2', 20),
    ('param3', 30),
    # ... 20 more parameters
)
```

### ❌ No Position Sizing
```python
# BAD: Fixed size regardless of risk
def buy_signal(self):
    self.buy(size=100)  # Always 100 shares
```

---

## Best Practices

### ✅ Modular Design
- Separate indicator setup from signal logic
- Reusable components
- Clear abstractions

### ✅ Parameter Validation
```python
def __init__(self):
    assert 0 < self.params.risk_per_trade < 0.1, "Risk too high"
    assert self.params.stop_loss_pct > 0, "Stop loss must be positive"
```

### ✅ Logging
```python
def next(self):
    self.log(f'Close: {self.data.close[0]:.2f}, Signal: {self.generate_signal()}')
```

### ✅ Documentation
```python
class Strategy(BaseStrategy):
    """
    Moving Average Crossover Strategy
    
    Entry: Fast MA crosses above Slow MA
    Exit: Fast MA crosses below Slow MA
    
    Parameters:
        fast_period: Fast MA period (default: 10)
        slow_period: Slow MA period (default: 30)
    
    Risk Management:
        Stop Loss: 5%
        Position Size: 2% risk per trade
    """
```

---

## Related

- [risk-management.md](risk-management.md) - Risk management details
- [backtesting-standards.md](backtesting-standards.md) - Testing standards
- [../examples/](../examples/) - Strategy examples

---

**Last Updated**: 2026-03-19  
**Version**: 1.0.0