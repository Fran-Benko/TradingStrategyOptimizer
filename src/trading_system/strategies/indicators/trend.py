"""
Trend indicators.

Provides common trend-following technical indicators.
"""

from typing import Union, Tuple

import numpy as np
import pandas as pd


def calculate_sma(
    prices: Union[pd.Series, np.ndarray],
    period: int
) -> pd.Series:
    """
    Calculate Simple Moving Average (SMA).

    Args:
        prices: Price series
        period: Moving average period

    Returns:
        Series with SMA values

    Example:
        >>> sma_20 = calculate_sma(data["close"], period=20)
    """
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)

    return prices.rolling(window=period, min_periods=period).mean()


def calculate_ema(
    prices: Union[pd.Series, np.ndarray],
    period: int
) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).

    Args:
        prices: Price series
        period: EMA period

    Returns:
        Series with EMA values

    Example:
        >>> ema_12 = calculate_ema(data["close"], period=12)
    """
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)

    return prices.ewm(span=period, adjust=False).mean()


def calculate_bollinger_bands(
    prices: Union[pd.Series, np.ndarray],
    period: int = 20,
    num_std: float = 2.0
) -> pd.DataFrame:
    """
    Calculate Bollinger Bands.

    Bollinger Bands are a volatility indicator that consists of
    a middle band (SMA) and two outer bands at standard deviations.

    Args:
        prices: Price series
        period: Moving average period (default: 20)
        num_std: Number of standard deviations (default: 2.0)

    Returns:
        DataFrame with columns: upper, middle, lower

    Example:
        >>> bb = calculate_bollinger_bands(data["close"])
        >>> print(f"Upper: {bb['upper'].iloc[-1]:.2f}")
    """
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)

    middle = calculate_sma(prices, period)
    std = prices.rolling(window=period, min_periods=period).std()

    return pd.DataFrame({
        "upper": middle + (std * num_std),
        "middle": middle,
        "lower": middle - (std * num_std)
    })


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Calculate Average True Range (ATR).

    ATR is a volatility indicator that measures market volatility.
    It's commonly used for setting stop losses.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period (default: 14)

    Returns:
        Series with ATR values

    Example:
        >>> atr = calculate_atr(data["high"], data["low"], data["close"])
        >>> print(f"ATR: {atr.iloc[-1]:.2f}")
    """
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    atr = true_range.rolling(window=period, min_periods=period).mean()

    return atr


def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.DataFrame:
    """
    Calculate Average Directional Index (ADX).

    ADX is a trend strength indicator. Values above 25 indicate
    a strong trend, values below 20 indicate a weak trend.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ADX period (default: 14)

    Returns:
        DataFrame with columns: adx, plus_di, minus_di

    Example:
        >>> adx = calculate_adx(data["high"], data["low"], data["close"])
        >>> print(f"ADX: {adx['adx'].iloc[-1]:.2f}")
    """
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr = calculate_atr(high, low, close, period=1)

    plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)

    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

    adx = dx.rolling(window=period).mean()

    return pd.DataFrame({
        "adx": adx,
        "plus_di": plus_di,
        "minus_di": minus_di
    })


def calculate_supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0
) -> pd.DataFrame:
    """
    Calculate Supertrend indicator.

    Supertrend is a trend-following indicator that uses ATR for
    volatility adjustment.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period (default: 10)
        multiplier: ATR multiplier (default: 3.0)

    Returns:
        DataFrame with columns: supertrend, direction

    Example:
        >>> st = calculate_supertrend(data["high"], data["low"], data["close"])
        >>> print(f"Supertrend: {st['supertrend'].iloc[-1]:.2f}")
    """
    atr = calculate_atr(high, low, close, period)

    hl2 = (high + low) / 2
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)

    supertrend.iloc[0] = upperband.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(close)):
        if close.iloc[i] > upperband.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lowerband.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == 1:
            supertrend.iloc[i] = lowerband.iloc[i]
        else:
            supertrend.iloc[i] = upperband.iloc[i]

    return pd.DataFrame({
        "supertrend": supertrend,
        "direction": direction
    })
