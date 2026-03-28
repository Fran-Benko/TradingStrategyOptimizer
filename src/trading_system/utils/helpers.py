"""
Helper utilities for the trading system.

Provides common utility functions for:
- Date validation and manipulation
- Symbol normalization
- List operations
- Financial calculations
- Data formatting
- DataFrame operations
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from pandas import DataFrame, Series, Timestamp


def validate_date_range(
    start: Union[str, datetime, pd.Timestamp],
    end: Union[str, datetime, pd.Timestamp],
    allow_future: bool = False,
    max_range_days: Optional[int] = None
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Validate and normalize a date range.
    
    Ensures start date is before end date and both are valid.
    
    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        allow_future: Whether to allow future dates
        max_range_days: Maximum allowed range in days
        
    Returns:
        Tuple of (start, end) as pandas Timestamps
        
    Raises:
        ValueError: If dates are invalid or range is too large
        
    Example:
        >>> start, end = validate_date_range("2024-01-01", "2024-12-31")
        >>> print(f"Range: {start} to {end}")
    """
    # Convert to pandas Timestamp
    if isinstance(start, str):
        try:
            start = pd.to_datetime(start)
        except Exception as e:
            raise ValueError(f"Invalid start date format: {start}") from e
    
    if isinstance(end, str):
        try:
            end = pd.to_datetime(end)
        except Exception as e:
            raise ValueError(f"Invalid end date format: {end}") from e
    
    if isinstance(start, datetime):
        start = pd.Timestamp(start)
    if isinstance(end, datetime):
        end = pd.Timestamp(end)
    
    # Ensure we have Timestamp objects
    if not isinstance(start, pd.Timestamp) or not isinstance(end, pd.Timestamp):
        raise ValueError(f"Invalid date types: start={type(start)}, end={type(end)}")
    
    # Check for future dates
    now = pd.Timestamp.now()
    if not allow_future:
        if start > now or end > now:
            raise ValueError("Future dates not allowed unless allow_future=True")
    
    # Ensure start is before or equal to end
    if start > end:
        raise ValueError(f"Start date ({start}) must be before or equal to end date ({end})")
    
    # Check max range
    if max_range_days is not None:
        range_days = (end - start).days
        if range_days > max_range_days:
            raise ValueError(
                f"Date range ({range_days} days) exceeds maximum allowed ({max_range_days} days)"
            )
    
    return start, end


def normalize_symbol(symbol: str, exchange: Optional[str] = None) -> str:
    """
    Normalize a ticker symbol to a standard format.
    
    Handles common variations like:
    - Lowercase/uppercase conversion
    - Exchange suffixes (.SP, .V, etc.)
    - Special characters
    
    Args:
        symbol: The ticker symbol to normalize
        exchange: Optional exchange code for context
        
    Returns:
        Normalized symbol string
        
    Example:
        >>> normalize_symbol("aapl")
        'AAPL'
        >>> normalize_symbol("BRK.B")
        'BRK.B'
        >>> normalize_symbol("ETH/USD", "coinbase")
        'ETH/USD'
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string")
    
    # Strip whitespace
    symbol = symbol.strip()
    
    # Remove common exchange prefixes
    symbol = re.sub(r'^(NYSE|NASDAQ|AMEX|SP):\s*', '', symbol, flags=re.IGNORECASE)
    
    # Handle crypto symbols (usually base/quote format)
    if '/' in symbol:
        parts = symbol.split('/')
        return '/'.join(part.strip().upper() for part in parts)
    
    # Handle equity symbols with class suffix (e.g., BRK.B -> keep as is)
    if '.' in symbol:
        parts = symbol.split('.')
        if len(parts) == 2 and len(parts[1]) == 1:
            # Class suffix like BRK.A, BRK.B
            return f"{parts[0].upper()}.{parts[1].upper()}"
    
    # Standard normalization: uppercase, no spaces
    symbol = symbol.upper().replace(' ', '').replace('-', '')
    
    # Handle common suffix patterns
    exchange_suffixes = {
        'SP': '.SP',  # S&P 500
        'V': '.V',    # Vanguard
    }
    
    if exchange and exchange.upper() in exchange_suffixes:
        suffix = exchange_suffixes[exchange.upper()]
        if not symbol.endswith(suffix):
            symbol = f"{symbol}{suffix}"
    
    return symbol


def chunk_list(
    lst: Sequence[Any],
    n: int,
    fill_value: Optional[Any] = None
) -> Generator[List[Any], None, None]:
    """
    Split a list into chunks of size n.
    
    Useful for batch processing or API requests with size limits.
    
    Args:
        lst: The list to chunk
        n: Chunk size (must be positive)
        fill_value: Value to pad last chunk if needed
        
    Yields:
        Lists of size n (last may be smaller unless fill_value provided)
        
    Example:
        >>> list(chunk_list([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
        >>> list(chunk_list([1, 2, 3], 2, fill_value=0))
        [[1, 2], [3, 0]]
    """
    if n <= 0:
        raise ValueError(f"Chunk size must be positive, got {n}")
    
    length = len(lst)
    
    for i in range(0, length, n):
        chunk = list(lst[i:i + n])
        
        # Pad last chunk if fill_value provided
        if fill_value is not None and len(chunk) < n:
            chunk.extend([fill_value] * (n - len(chunk)))
        
        yield chunk


def calculate_returns(
    prices: Union[Series, List[float], np.ndarray],
    method: str = "simple",
    periods: int = 1
) -> Series:
    """
    Calculate returns from price data.
    
    Supports simple returns, log returns, and cumulative returns.
    
    Args:
        prices: Price series or list of prices
        method: Return calculation method ('simple', 'log', 'cumulative')
        periods: Number of periods for calculating returns
        
    Returns:
        Series of returns
        
    Example:
        >>> prices = [100, 102, 101, 105]
        >>> calculate_returns(prices)
        0         NaN
        1    0.020000
        2   -0.009804
        3    0.039604
        dtype: float64
    """
    if isinstance(prices, list):
        prices = Series(prices)
    elif isinstance(prices, np.ndarray):
        prices = Series(prices)
    
    if not isinstance(prices, Series):
        raise TypeError("prices must be a Series, list, or numpy array")
    
    if method == "simple":
        returns = prices.pct_change(periods=periods)
    elif method == "log":
        returns = np.log(prices / prices.shift(periods))
    elif method == "cumulative":
        simple_returns = prices.pct_change(periods=periods)
        returns = (1 + simple_returns).cumprod() - 1
    else:
        raise ValueError(f"Unknown method: {method}. Use 'simple', 'log', or 'cumulative'")
    
    return returns


def resample_ohlcv(
    data: DataFrame,
    timeframe: str,
    agg_config: Optional[Dict[str, str]] = None
) -> DataFrame:
    """
    Resample OHLCV data to a different timeframe.
    
    Properly aggregates Open, High, Low, Close, Volume columns
    for the new timeframe.
    
    Args:
        data: DataFrame with OHLCV data and DatetimeIndex
        timeframe: Target timeframe (e.g., '5T', '1H', '1D', 'W')
        agg_config: Custom aggregation config for non-standard columns
        
    Returns:
        Resampled DataFrame
        
    Raises:
        ValueError: If required columns are missing
        
    Example:
        >>> minute_data = load_data("AAPL", "1T")
        >>> hourly_data = resample_ohlcv(minute_data, "1H")
    """
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    data_cols = [c.lower() for c in data.columns]
    
    # Validate columns exist (case-insensitive)
    missing = [col for col in required_cols if col not in data_cols]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Create lowercase column mapping
    col_map = {c.lower(): c for c in data.columns}
    
    # Default aggregation configuration
    if agg_config is None:
        agg_config = {
            col_map['open']: 'first',
            col_map['high']: 'max',
            col_map['low']: 'min',
            col_map['close']: 'last',
            col_map['volume']: 'sum',
        }
        
        # Add any additional numeric columns with mean aggregation
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in agg_config:
                agg_config[col] = 'mean'
    
    # Perform resampling
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a DatetimeIndex for resampling")
    
    resampled = data.resample(timeframe).agg(agg_config)
    
    # Drop rows with all NaN values
    resampled = resampled.dropna(how='all')
    
    return resampled


def format_currency(
    value: float,
    currency: str = "USD",
    decimals: int = 2,
    include_symbol: bool = True,
    include_sign: bool = False
) -> str:
    """
    Format a numeric value as currency.
    
    Args:
        value: The numeric value to format
        currency: Currency code (USD, EUR, GBP, etc.)
        decimals: Number of decimal places
        include_symbol: Whether to include currency symbol
        include_sign: Whether to include + for positive values
        
    Returns:
        Formatted currency string
        
    Example:
        >>> format_currency(1234.56)
        '$1,234.56'
        >>> format_currency(-500, include_sign=True)
        '-$500.00'
        >>> format_currency(1000000, currency="EUR")
        '€1,000,000.00'
    """
    # Currency symbols
    symbols: Dict[str, str] = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CNY': '¥',
        'CHF': 'CHF ',
        'CAD': 'C$',
        'AUD': 'A$',
    }
    
    symbol = symbols.get(currency.upper(), f"{currency} ")
    
    # Determine sign
    sign = ""
    if include_sign and value > 0:
        sign = "+"
    elif value < 0:
        sign = "-"
        value = abs(value)
    
    # Format number
    formatted = f"{value:,.{decimals}f}"
    
    if include_symbol:
        return f"{sign}{symbol}{formatted}"
    return f"{sign}{formatted}"


def format_percentage(
    value: float,
    decimals: int = 2,
    include_sign: bool = True,
    include_symbol: bool = True
) -> str:
    """
    Format a numeric value as a percentage.
    
    Args:
        value: The value (0.05 = 5%, or 5 = 5%)
        decimals: Number of decimal places
        include_sign: Whether to include + for positive values
        include_symbol: Whether to include % symbol
        
    Returns:
        Formatted percentage string
        
    Example:
        >>> format_percentage(0.05)
        '5.00%'
        >>> format_percentage(-0.15, include_sign=True)
        '-15.00%'
        >>> format_percentage(5.5, decimals=1, include_symbol=False)
        '+5.5'
    """
    # Determine sign
    sign = ""
    if include_sign and value > 0:
        sign = "+"
    elif value < 0:
        sign = "-"
        value = abs(value)
    
    # Convert to percentage if in decimal form
    if abs(value) < 10:  # Likely a decimal (0.05)
        value = value * 100
    
    # Format number
    formatted = f"{value:.{decimals}f}"
    
    if include_symbol:
        return f"{sign}{formatted}%"
    return f"{sign}{formatted}"


def merge_dataframes(
    dfs: List[DataFrame],
    how: str = "outer",
    on: Optional[str] = None,
    left_on: Optional[str] = None,
    right_on: Optional[str] = None,
    sort: bool = True,
    validate: Optional[str] = None
) -> DataFrame:
    """
    Merge multiple DataFrames efficiently.
    
    A convenience wrapper around pd.merge that handles multiple DataFrames
    in a single call.
    
    Args:
        dfs: List of DataFrames to merge
        how: Type of merge ('inner', 'outer', 'left', 'right')
        on: Column name to join on (if same in all DataFrames)
        left_on: Column name in left DataFrame(s)
        right_on: Column name in right DataFrame(s)
        sort: Whether to sort by join keys
        validate: Validate merge type ('1:1', '1:m', 'm:1', 'm:m')
        
    Returns:
        Merged DataFrame
        
    Raises:
        ValueError: If fewer than 2 DataFrames provided
        
    Example:
        >>> df1 = DataFrame({'date': dates, 'price': prices1})
        >>> df2 = DataFrame({'date': dates, 'volume': volumes})
        >>> merged = merge_dataframes([df1, df2], on='date')
    """
    if len(dfs) < 2:
        raise ValueError("At least 2 DataFrames required for merge")
    
    if len(dfs) == 2:
        return pd.merge(
            dfs[0],
            dfs[1],
            how=how,
            on=on,
            left_on=left_on,
            right_on=right_on,
            sort=sort,
            validate=validate
        )
    
    # Merge multiple DataFrames iteratively
    result = dfs[0]
    
    for df in dfs[1:]:
        result = pd.merge(
            result,
            df,
            how=how,
            on=on,
            left_on=left_on,
            right_on=right_on,
            sort=sort,
            validate=validate if len(dfs) == 2 else None  # Only validate final
        )
    
    return result


def calculate_sharpe_ratio(
    returns: Union[Series, List[float]],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Calculate the Sharpe ratio for a return series.
    
    Args:
        returns: Series or list of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods in a year (252 for daily)
        
    Returns:
        Sharpe ratio
        
    Example:
        >>> returns = calculate_returns(prices)
        >>> sharpe = calculate_sharpe_ratio(returns)
    """
    if isinstance(returns, list):
        returns = Series(returns)
    
    excess_returns = returns - (risk_free_rate / periods_per_year)
    
    if excess_returns.std() == 0:
        return 0.0
    
    sharpe = excess_returns.mean() / excess_returns.std()
    return sharpe * np.sqrt(periods_per_year)


def calculate_max_drawdown(
    equity_curve: Union[Series, List[float]]
) -> Tuple[float, int, int]:
    """
    Calculate maximum drawdown from an equity curve.
    
    Args:
        equity_curve: Series or list of equity values
        
    Returns:
        Tuple of (max_drawdown, peak_index, trough_index)
        
    Example:
        >>> equity = [100, 110, 105, 95, 100, 120]
        >>> max_dd, peak, trough = calculate_max_drawdown(equity)
    """
    if isinstance(equity_curve, list):
        equity_curve = Series(equity_curve)
    
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max
    
    max_dd_idx = drawdown.idxmin()
    
    # Find corresponding peak
    peak_value = running_max.loc[:max_dd_idx].idxmax()
    
    return float(drawdown.loc[max_dd_idx]), int(peak_value), int(max_dd_idx)


def align_dataframes(
    *dfs: DataFrame,
    how: str = "inner",
    freq: Optional[str] = None
) -> List[DataFrame]:
    """
    Align multiple DataFrames to a common index.
    
    Useful for ensuring different data sources have matching timestamps.
    
    Args:
        *dfs: DataFrames to align
        how: Merge type for alignment ('inner', 'outer')
        freq: Optional frequency to reindex to (e.g., '1D', '1H')
        
    Returns:
        List of aligned DataFrames
        
    Example:
        >>> aligned = align_dataframes(df1, df2, df3, freq='1D')
    """
    if not dfs:
        return []
    
    # Find common index
    common_idx = dfs[0].index
    
    for df in dfs[1:]:
        if how == "inner":
            common_idx = common_idx.intersection(df.index)
        else:  # outer
            common_idx = common_idx.union(df.index)
    
    # Reindex to common index
    result = []
    for df in dfs:
        reindexed = df.reindex(common_idx)
        result.append(reindexed)
    
    # Add frequency if specified
    if freq:
        full_idx = pd.date_range(
            start=common_idx.min(),
            end=common_idx.max(),
            freq=freq
        )
        result = [df.reindex(full_idx) for df in result]
    
    return result
