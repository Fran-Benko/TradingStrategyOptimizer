# Code Generator Skill

## Descripción

Genera código Python siguiendo los estándares del proyecto de trading system. Utiliza templates y patrones predefinidos para crear módulos, clases y funciones de manera consistente.

## Activación

```
Genera código para [descripción]
```

## Templates Disponibles

### 1. Data Fetcher

```python
"""
[Module description]

Generates data fetcher implementations following the project's patterns.
"""

from typing import Protocol, List, Dict, Optional
from datetime import datetime
import pandas as pd
import logging

from trading_system.exceptions import DataFetchError
from trading_system.protocols import DataFetcher

logger = logging.getLogger(__name__)


class BaseDataFetcher(Protocol):
    """Protocol for data fetchers."""
    
    def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol."""
        ...
    
    def fetch_batch(
        self,
        symbols: List[str],
        start: str,
        end: str,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols."""
        ...


class [Source]DataFetcher:
    """
    Data fetcher for [Source] API.
    
    Args:
        api_key: API key for authentication
        base_url: Base URL for the API
        cache: Optional cache instance
        rate_limiter: Optional rate limiter
    
    Example:
        >>> fetcher = YahooDataFetcher()
        >>> data = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31")
        >>> print(data.head())
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.example.com",
        cache: Optional[Any] = None,
        rate_limiter: Optional[Any] = None
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.cache = cache
        self.rate_limiter = rate_limiter
        self._session = None
    
    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            if self.api_key:
                self._session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        return self._session
    
    def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format
            interval: Data interval (1d, 1h, 5m, etc.)
        
        Returns:
            DataFrame with columns: open, high, low, close, volume
        
        Raises:
            DataFetchError: If fetch fails
        """
        cache_key = f"{symbol}_{start}_{end}_{interval}"
        
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached
        
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()
        
        try:
            data = self._fetch_from_api(symbol, start, end, interval)
            
            if self.cache:
                self.cache.set(cache_key, data)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            raise DataFetchError(f"Failed to fetch {symbol}: {e}") from e
    
    def _fetch_from_api(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str
    ) -> pd.DataFrame:
        """Fetch data from API. Override in subclass."""
        raise NotImplementedError
    
    def fetch_batch(
        self,
        symbols: List[str],
        start: str,
        end: str,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            start: Start date
            end: End date
            interval: Data interval
        
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.fetch(symbol, start, end, interval)
            except DataFetchError as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")
                results[symbol] = pd.DataFrame()
        
        return results
```

### 2. Strategy Template

```python
"""
[Strategy name] Strategy

Implements [description of strategy].
"""

from typing import Optional, List
from dataclasses import dataclass
import pandas as pd
import numpy as np
import logging

from trading_system.strategies.base import BaseStrategy, Signal

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Configuration for [Strategy] strategy."""
    
    period: int = 14
    overbought: float = 70.0
    oversold: float = 30.0


class [StrategyName]Strategy(BaseStrategy):
    """
    [Strategy description].
    
    This strategy [explain logic].
    
    Args:
        config: Strategy configuration
    
    Example:
        >>> config = RSIStrategyConfig(period=14, overbought=70, oversold=30)
        >>> strategy = RSIStrategy(config)
        >>> signals = strategy.generate_signals(data)
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()
        self.name = "[StrategyName]Strategy"
    
    @property
    def required_indicators(self) -> List[str]:
        """Indicators required by this strategy."""
        return ["close"]
    
    def generate_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Generate trading signals.
        
        Args:
            data: DataFrame with OHLCV data
        
        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        close = data["close"].values
        signals = np.zeros(len(close))
        
        # Strategy logic here
        # ...
        
        return signals
    
    def get_parameters(self) -> dict:
        """Get current strategy parameters."""
        return {
            "period": self.config.period,
            "overbought": self.config.overbought,
            "oversold": self.config.oversold
        }
```

### 3. Indicator Template

```python
"""
Technical Indicators

Provides common technical indicators for trading strategies.
"""

from typing import Union
import numpy as np
import pandas as pd


def calculate_rsi(prices: Union[pd.Series, np.ndarray], period: int = 14) -> np.ndarray:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        prices: Price series
        period: RSI period (default: 14)
    
    Returns:
        RSI values between 0 and 100
    
    Example:
        >>> rsi = calculate_rsi(data["close"], period=14)
        >>> print(f"Current RSI: {rsi[-1]:.2f}")
    """
    if isinstance(prices, pd.Series):
        prices = prices.values
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    rsi = np.zeros(len(prices))
    rsi[:period] = 50
    
    for i in range(period, len(prices)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
    
    return rsi
```

## Uso

### Generar nuevo módulo

```
Genera módulo de fetcher para Binance
Incluye: retry logic, rate limiting, cache
```

### Generar clase

```
Genera clase Strategy para media móvil
Con: crossover signals, parameter validation
```

### Generar utilidad

```
Genera módulo de validation para symbols
Incluye: format checking, exchange validation
```

## Configuración

El skill respeta la configuración del proyecto:
- PEP 8 formatting
- Type hints obligatorios
- Google-style docstrings
- Logging estructurado

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19
