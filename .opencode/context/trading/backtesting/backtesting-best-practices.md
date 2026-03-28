# Backtesting Best Practices

## Descripción

Mejores prácticas para backtesting de estrategias de trading.

## Principios Fundamentales

### 1. Datos de Calidad

```python
# Validar datos antes de backtesting
def validate_data(data: pd.DataFrame) -> bool:
    checks = {
        "no_nan": not data.isnull().any().any(),
        "no_duplicates": not data.index.duplicated().any(),
        "reasonable_range": (data["close"] > 0).all(),
        "ohlc_consistency": (data["high"] >= data["low"]).all()
    }
    return all(checks.values())
```

### 2. Simulación Realista

```python
class RealisticBacktester:
    def __init__(self, commission: float = 0.001, slippage: float = 0.0005):
        self.commission = commission
        self.slippage = slippage
    
    def execute_trade(self, signal, price, quantity):
        # Apply slippage
        execution_price = price * (1 + self.slippage * signal)
        
        # Calculate commission
        trade_value = abs(execution_price * quantity)
        commission_cost = trade_value * self.commission
        
        return execution_price, commission_cost
```

### 3. Walk-Forward Analysis

```python
def walk_forward_analysis(strategy, data, train_size=252, test_size=63):
    """
    Valida robustez de estrategia con walk-forward.
    
    Args:
        train_size: Período de entrenamiento en días
        test_size: Período de test en días
    """
    results = []
    
    for i in range(train_size, len(data) - test_size, test_size):
        train_data = data.iloc[i - train_size:i]
        test_data = data.iloc[i:i + test_size]
        
        # Optimize on train
        best_params = optimize(strategy, train_data)
        
        # Test on unseen data
        test_result = backtest(strategy, test_data, best_params)
        
        results.append({
            "train_period": f"{train_data.index[0]} to {train_data.index[-1]}",
            "test_period": f"{test_data.index[0]} to {test_data.index[-1]}",
            "train_sharpe": calculate_sharpe(train_data),
            "test_sharpe": test_result.sharpe,
            "params": best_params
        })
    
    return pd.DataFrame(results)
```

## Evitar Biases

### Look-Ahead Bias

```python
# ❌ MAL: Usa datos futuros
def bad_strategy(data):
    future_return = data["close"].shift(-1)  # ¡No hacer esto!
    return np.where(data["close"] < future_return, 1, -1)

# ✅ BIEN: Solo usa datos disponibles
def good_strategy(data):
    sma = data["close"].rolling(20).mean()  # Solo datos pasados
    return np.where(data["close"] > sma, 1, -1)
```

### Survivorship Bias

```python
# Incluir símbolos que fallaron en el período
def get_universe(date, universe_size=1000):
    all_stocks = get_stocks_existing_on(date)
    return sample(all_stocks, universe_size)
```

### Selection Bias

```python
# No seleccionar símbolos basándose en resultados futuros
def select_symbols():
    # ❌ Basado en data snooping
    # return top_performers(past_year)
    
    # ✅ Selección aleatoria o basada en criterios predefinidos
    return get_random_universe(size=100)
```

## Métricas a Reportar

```python
class BacktestReport:
    def __init__(self, results):
        self.total_return = calculate_total_return(results)
        self.sharpe_ratio = calculate_sharpe(results)
        self.max_drawdown = calculate_max_drawdown(results)
        self.win_rate = calculate_win_rate(results)
        self.profit_factor = calculate_profit_factor(results)
        self.trade_count = len(results.trades)
        self.avg_trade = np.mean(results.returns)
    
    def summary(self):
        return f"""
        === Backtest Results ===
        
        Total Return: {self.total_return:.2%}
        Sharpe Ratio: {self.sharpe_ratio:.2f}
        Max Drawdown: {self.max_drawdown:.2%}
        Win Rate: {self.win_rate:.2%}
        Profit Factor: {self.profit_factor:.2f}
        Trade Count: {self.trade_count}
        Avg Trade: {self.avg_trade:.4f}
        """
```

## Validación Monte Carlo

```python
def monte_carlo_validation(backtest_result, n_simulations=1000):
    """Valida que resultados no sean por suerte."""
    trades = backtest_result.trades
    
    simulated_returns = []
    for _ in range(n_simulations):
        # Shuffle trade returns
        shuffled = np.random.choice(trades, size=len(trades), replace=True)
        simulated_returns.append(np.sum(shuffled))
    
    percentile = stats.percentileofscore(simulated_returns, 
                                         backtest_result.total_return)
    
    return {
        "real_result_percentile": percentile,
        "is_significant": percentile > 95 or percentile < 5
    }
```

---

**Última actualización**: 2026-03-19
