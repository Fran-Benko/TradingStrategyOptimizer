---
name: data-fetcher
description: Fetches market data from Yahoo Finance, Alpaca, and Google Finance. Handles rate limiting, caching, validation, and fallback logic. Returns normalized OHLCV data ready for backtesting.
---

# Data Fetcher Skill

This skill provides a unified interface to fetch market data from multiple sources with automatic fallback, caching, and validation.

## When to Use This Skill

- Fetching historical price data for backtesting
- Getting real-time market quotes
- Validating symbol existence
- Downloading data for multiple symbols
- Need reliable data with automatic fallback

## What This Skill Does

1. **Multi-Source Fetching**: Tries Alpaca → Yahoo Finance → Google Finance
2. **Rate Limiting**: Respects API limits for each source
3. **Caching**: Caches data to minimize API calls
4. **Validation**: Validates OHLCV data integrity
5. **Normalization**: Returns consistent format regardless of source
6. **Error Handling**: Graceful fallback on failures

## How to Use

### Basic Usage

```
Fetch historical data for AAPL from 2023-01-01 to 2024-01-01
```

```
Get real-time quote for TSLA
```

```
Download daily data for SPY, QQQ, IWM for the last year
```

### With Specific Source

```
Fetch AAPL data from Yahoo Finance for backtesting
```

```
Get real-time data from Alpaca for MSFT
```

### Batch Fetching

```
Fetch historical data for these symbols: AAPL, GOOGL, MSFT, AMZN
Date range: 2023-01-01 to 2024-01-01
Interval: 1 day
```

## Data Sources

### Yahoo Finance
- **Best for**: Historical data, backtesting
- **Rate limit**: ~2000 requests/hour
- **Intervals**: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo
- **Delay**: ~15 minutes for real-time

### Alpaca
- **Best for**: Real-time data, paper trading
- **Rate limit**: 200 requests/minute (free tier)
- **Intervals**: 1min, 5min, 15min, 30min, 1hour, 1day
- **Delay**: Real-time (with subscription)

### Google Finance
- **Best for**: Fallback, validation
- **Rate limit**: Conservative (100/min)
- **Intervals**: 1d (primarily)
- **Delay**: Varies

## Output Format

### Historical Data
Returns pandas DataFrame with:
```
Date (index) | open | high | low | close | volume
2023-01-01   | 130.5| 132.1| 129.8| 131.5 | 1000000
2023-01-02   | 131.6| 133.2| 131.0| 132.8 | 1200000
...
```

### Real-time Quote
Returns dictionary with:
```python
{
    'symbol': 'AAPL',
    'price': 175.43,
    'volume': 52000000,
    'timestamp': '2024-01-15 16:00:00',
    'source': 'alpaca'
}
```

## Examples

### Example 1: Simple Historical Fetch

**User**: "Fetch AAPL data for 2023"

**Output**:
```
✅ Fetched 252 trading days for AAPL
Source: Yahoo Finance
Date range: 2023-01-03 to 2023-12-29
Interval: 1 day

Data preview:
            open    high     low   close     volume
2023-01-03  130.28  130.90  124.17  125.07  112117500
2023-01-04  126.89  128.66  125.08  126.36   89113600
...

Data saved to: .cache/AAPL_2023-01-01_2023-12-31_1d.csv
```

### Example 2: Real-time Quote

**User**: "Get current price for TSLA"

**Output**:
```
✅ Real-time quote for TSLA

Price: $242.84
Volume: 125,432,100
Change: +$5.23 (+2.20%)
Source: Alpaca
Timestamp: 2024-01-15 15:59:58 EST

Market Status: Open
```

### Example 3: Batch Fetch with Fallback

**User**: "Fetch data for AAPL, INVALID_SYMBOL, GOOGL"

**Output**:
```
Fetching data for 3 symbols...

✅ AAPL: 252 days (Yahoo Finance)
❌ INVALID_SYMBOL: Symbol not found (tried all sources)
✅ GOOGL: 252 days (Alpaca)

Summary:
- Successful: 2/3 symbols
- Failed: 1/3 symbols
- Total data points: 504

Data saved to: .cache/batch_2024-01-15_143022/
```

## Advanced Features

### Caching

Data is automatically cached to reduce API calls:
- Historical data: Cached for 24 hours
- Intraday data: Cached for 1 hour
- Real-time quotes: Not cached

Cache location: `.cache/market_data/`

### Validation

All data is validated for:
- Required columns present (OHLCV)
- No negative values
- High >= Low
- Open/Close within High/Low range
- No missing data
- Outlier detection

### Rate Limiting

Automatic rate limiting per source:
- Yahoo: 2000 req/hour
- Alpaca: 200 req/minute
- Google: 100 req/minute

If limit reached, automatically waits or switches source.

### Retry Logic

Automatic retry with exponential backoff:
- Max 3 retries
- Backoff: 1s, 2s, 4s
- Falls back to next source on failure

## Configuration

### API Keys

Set environment variables:
```bash
export ALPACA_API_KEY=your_key
export ALPACA_SECRET_KEY=your_secret
export ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### Source Priority

Default priority:
1. Alpaca (most reliable, real-time)
2. Yahoo Finance (free, good historical)
3. Google Finance (fallback)

Can be customized per request.

## Error Handling

### Common Errors

**Symbol Not Found**:
```
❌ Symbol 'XYZ' not found
Tried sources: Alpaca, Yahoo Finance, Google Finance
Suggestion: Check symbol spelling or try alternative ticker
```

**Rate Limit Exceeded**:
```
⚠️ Rate limit reached for Yahoo Finance
Switching to Alpaca...
✅ Data fetched successfully from Alpaca
```

**API Failure**:
```
❌ Alpaca API error: Connection timeout
Retrying with Yahoo Finance...
✅ Data fetched successfully from Yahoo Finance
```

## Tips

- Use Yahoo Finance for historical backtesting (free, reliable)
- Use Alpaca for real-time data and paper trading
- Cache is your friend - reuse data when possible
- Batch fetch multiple symbols to save time
- Validate symbols before fetching large date ranges

## Related Skills

- `backtest-runner` - Run backtests with fetched data
- `strategy-optimizer` - Optimize strategies using historical data
- `metrics-calculator` - Calculate metrics from price data

## Technical Details

**Implementation**: Python with yfinance, alpaca-py, requests  
**Dependencies**: pandas, numpy, requests, yfinance, alpaca-py  
**Cache Format**: Parquet (fast, compressed)  
**Validation**: OHLCV integrity checks, outlier detection

---

**Version**: 1.0.0  
**Last Updated**: 2026-03-19  
**Maintained By**: Trading Team