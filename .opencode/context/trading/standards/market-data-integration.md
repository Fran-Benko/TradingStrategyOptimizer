<!-- Context: trading/data-integration | Priority: critical | Version: 1.0 | Updated: 2026-03-19 -->

# Market Data Integration Standards

**Purpose**: Standards for integrating Yahoo Finance, Alpaca, and Google Finance  
**Priority**: CRITICAL - Load before implementing data fetchers

---

## Core Principles

1. **Unified Interface**: All data sources implement same protocol
2. **Fail Gracefully**: Handle API failures without crashing
3. **Rate Limiting**: Respect API limits
4. **Data Quality**: Validate all fetched data
5. **Caching**: Minimize redundant API calls

---

## Data Fetcher Protocol

### Interface Definition

```python
from typing import Protocol, Optional
from datetime import datetime
import pandas as pd

class DataFetcher(Protocol):
    """
    Unified interface for all market data sources
    ALL fetchers MUST implement this protocol
    """
    
    def fetch_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data
        
        Returns DataFrame with columns:
        - Date (index)
        - Open, High, Low, Close, Volume
        """
        ...
    
    def fetch_realtime(
        self,
        symbol: str
    ) -> dict:
        """
        Fetch current quote
        
        Returns dict with:
        - symbol, price, volume, timestamp
        """
        ...
    
    def validate_symbol(
        self,
        symbol: str
    ) -> bool:
        """Check if symbol exists"""
        ...
    
    def get_rate_limit(self) -> dict:
        """
        Return rate limit info
        
        Returns:
        - requests_per_minute
        - requests_remaining
        """
        ...
```

---

## Data Source Specifications

### 1. Yahoo Finance

**Library**: `yfinance`  
**Installation**: `pip install yfinance`

**Capabilities**:
- ✅ Historical data (daily, weekly, monthly)
- ✅ Intraday data (1m, 5m, 15m, 30m, 1h)
- ✅ Dividends and splits
- ✅ Company fundamentals
- ⚠️ Real-time delayed (~15 minutes)

**Rate Limits**:
- ~2000 requests/hour
- No official limit, but throttle to be safe

**Implementation Pattern**:
```python
import yfinance as yf
from datetime import datetime
import pandas as pd

class YahooFinanceFetcher:
    """Yahoo Finance data fetcher"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(
            max_calls=2000,
            period=3600  # 1 hour
        )
    
    def fetch_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch historical data"""
        with self.rate_limiter:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            return self._normalize_columns(df)
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names"""
        return df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
```

**Best Practices**:
- Cache historical data (rarely changes)
- Use batch requests when possible
- Handle missing data gracefully
- Validate data quality

---

### 2. Alpaca

**Library**: `alpaca-py`  
**Installation**: `pip install alpaca-py`

**Capabilities**:
- ✅ Real-time market data
- ✅ Historical bars (1min to 1day)
- ✅ Trade and quote data
- ✅ Market status
- ✅ Paper trading

**Rate Limits**:
- Free tier: 200 requests/minute
- Paid tier: Higher limits

**Authentication**:
```python
# Environment variables
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # or live
```

**Implementation Pattern**:
```python
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import os

class AlpacaFetcher:
    """Alpaca data fetcher"""
    
    def __init__(self):
        self.client = StockHistoricalDataClient(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY')
        )
        self.rate_limiter = RateLimiter(
            max_calls=200,
            period=60  # 1 minute
        )
    
    def fetch_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch historical bars"""
        with self.rate_limiter:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=self._convert_interval(interval),
                start=start_date,
                end=end_date
            )
            bars = self.client.get_stock_bars(request)
            return self._to_dataframe(bars)
    
    def _convert_interval(self, interval: str) -> TimeFrame:
        """Convert interval string to Alpaca TimeFrame"""
        mapping = {
            '1m': TimeFrame.Minute,
            '5m': TimeFrame(5, TimeFrame.Unit.Minute),
            '1h': TimeFrame.Hour,
            '1d': TimeFrame.Day
        }
        return mapping.get(interval, TimeFrame.Day)
```

**Best Practices**:
- Use WebSocket for real-time streaming
- Implement exponential backoff on errors
- Monitor rate limit headers
- Use paper trading for testing

---

### 3. Google Finance

**Library**: Custom implementation or `google-finance`  
**Installation**: `pip install google-finance` (if available)

**Capabilities**:
- ✅ Real-time quotes
- ✅ Historical data
- ✅ Market indices
- ⚠️ Less reliable than Yahoo/Alpaca

**Rate Limits**:
- Unofficial API, use cautiously
- Implement aggressive rate limiting

**Implementation Pattern**:
```python
import requests
from datetime import datetime
import pandas as pd

class GoogleFinanceFetcher:
    """Google Finance data fetcher (fallback source)"""
    
    def __init__(self):
        self.base_url = "https://www.google.com/finance"
        self.rate_limiter = RateLimiter(
            max_calls=100,
            period=60  # Conservative limit
        )
    
    def fetch_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch historical data"""
        with self.rate_limiter:
            # Implementation depends on available API
            # May require web scraping
            pass
    
    def fetch_realtime(self, symbol: str) -> dict:
        """Fetch real-time quote"""
        with self.rate_limiter:
            # Implement quote fetching
            pass
```

**Best Practices**:
- Use as fallback only
- Implement robust error handling
- Validate data quality carefully
- Consider legal/ToS implications

---

## Data Validation

### OHLCV Validation

```python
def validate_ohlcv(df: pd.DataFrame) -> bool:
    """
    Validate OHLCV data integrity
    
    Checks:
    1. Required columns present
    2. No negative values
    3. High >= Low
    4. Open/Close within High/Low range
    5. No missing data
    """
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    
    # Check columns
    if not all(col in df.columns for col in required_cols):
        return False
    
    # Check for negatives
    if (df[required_cols] < 0).any().any():
        return False
    
    # Check High >= Low
    if (df['high'] < df['low']).any():
        return False
    
    # Check Open/Close in range
    if ((df['open'] > df['high']) | (df['open'] < df['low'])).any():
        return False
    if ((df['close'] > df['high']) | (df['close'] < df['low'])).any():
        return False
    
    # Check for missing data
    if df[required_cols].isnull().any().any():
        return False
    
    return True
```

### Outlier Detection

```python
def detect_outliers(df: pd.DataFrame, column: str = 'close') -> pd.Series:
    """
    Detect outliers using IQR method
    
    Returns boolean series indicating outliers
    """
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - 3 * IQR
    upper_bound = Q3 + 3 * IQR
    
    return (df[column] < lower_bound) | (df[column] > upper_bound)
```

---

## Rate Limiting

### Rate Limiter Implementation

```python
import time
from threading import Lock
from collections import deque

class RateLimiter:
    """Thread-safe rate limiter"""
    
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self.lock = Lock()
    
    def __enter__(self):
        with self.lock:
            now = time.time()
            
            # Remove old calls
            while self.calls and self.calls[0] < now - self.period:
                self.calls.popleft()
            
            # Wait if limit reached
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.calls.popleft()
            
            self.calls.append(time.time())
    
    def __exit__(self, *args):
        pass
```

---

## Caching Strategy

### Cache Implementation

```python
import hashlib
import pickle
from pathlib import Path
from datetime import datetime, timedelta

class DataCache:
    """Cache for market data"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> Optional[pd.DataFrame]:
        """Get cached data if available and fresh"""
        cache_key = self._generate_key(symbol, start_date, end_date, interval)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        # Check if cache is fresh (< 1 day old for daily data)
        if interval == "1d":
            max_age = timedelta(days=1)
        else:
            max_age = timedelta(hours=1)
        
        file_age = datetime.now() - datetime.fromtimestamp(
            cache_file.stat().st_mtime
        )
        
        if file_age > max_age:
            return None
        
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    
    def set(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str,
        data: pd.DataFrame
    ):
        """Cache data"""
        cache_key = self._generate_key(symbol, start_date, end_date, interval)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
    
    def _generate_key(self, *args) -> str:
        """Generate cache key"""
        key_str = "_".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()
```

---

## Error Handling

### Retry Logic

```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, backoff_factor=2):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    wait_time = backoff_factor ** attempt
                    print(f"Attempt {attempt + 1} failed: {e}")
                    print(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        return wrapper
    return decorator

# Usage
@retry_on_failure(max_retries=3)
def fetch_data(symbol):
    return fetcher.fetch_historical(symbol, start, end)
```

---

## Data Source Priority

### Fallback Strategy

```python
class DataFetcherFactory:
    """Factory with fallback logic"""
    
    def __init__(self):
        self.sources = [
            ('alpaca', AlpacaFetcher()),
            ('yahoo', YahooFinanceFetcher()),
            ('google', GoogleFinanceFetcher())
        ]
    
    def fetch_with_fallback(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Try sources in order until success"""
        errors = []
        
        for source_name, fetcher in self.sources:
            try:
                data = fetcher.fetch_historical(
                    symbol, start_date, end_date
                )
                if validate_ohlcv(data):
                    return data
            except Exception as e:
                errors.append(f"{source_name}: {e}")
        
        raise Exception(f"All sources failed: {errors}")
```

---

## Success Criteria

Data integration is correct when:
- [ ] All three sources implement DataFetcher protocol
- [ ] Rate limiting working for each source
- [ ] Data validation passing
- [ ] Caching implemented
- [ ] Error handling robust
- [ ] Fallback logic working
- [ ] Tests passing

---

## Related

- [../architecture/data-flow.md](../../development/architecture/data-flow.md) - Data flow design
- [../errors/data-fetching-errors.md](../errors/data-fetching-errors.md) - Common errors
- [../lookup/data-sources-apis.md](../lookup/data-sources-apis.md) - API reference

---

**Last Updated**: 2026-03-19  
**Version**: 1.0.0