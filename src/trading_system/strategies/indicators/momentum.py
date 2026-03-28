"""
Momentum indicators.

Provides common momentum-based technical indicators.
"""

from typing import Union

import numpy as np
import pandas as pd


def calculate_rsi(
    prices: Union[pd.Series, np.ndarray],
    period: int = 14
) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).

    RSI is a momentum oscillator that measures the speed and magnitude
    of price changes. Traditional usage is that RSI above 70 indicates
    overbought and below 30 indicates oversold.

    Args:
        prices: Price series
        period: RSI period (default: 14)

    Returns:
        Series with RSI values (0-100)

    Example:
        >>> rsi = calculate_rsi(data["close"], period=14)
        >>> print(f"Current RSI: {rsi.iloc[-1]:.2f}")
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)

    deltas = prices.diff()

    gains = deltas.where(deltas > 0, 0.0)
    losses = -deltas.where(deltas < 0, 0.0)

    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi.iloc[:period] = 50.0

    return rsi


def calculate_macd(
    prices: Union[pd.Series, np.ndarray],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    MACD is a trend-following momentum indicator that shows the
    relationship between two moving averages of a security's price.

    Args:
        prices: Price series
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line period (default: 9)

    Returns:
        DataFrame with columns: macd, signal, histogram

    Example:
        >>> macd = calculate_macd(data["close"])
        >>> print(f"MACD: {macd['macd'].iloc[-1]:.2f}")
    """
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)

    ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
    ema_slow = prices.ewm(span=slow_period, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    })


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> pd.DataFrame:
    """
    Calculate Stochastic Oscillator.

    The stochastic oscillator is a momentum indicator that compares
    a closing price to its price range over a given period.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        k_period: %K period (default: 14)
        d_period: %D period (default: 3)

    Returns:
        DataFrame with columns: k, d

    Example:
        >>> stoch = calculate_stochastic(data["high"], data["low"], data["close"])
        >>> print(f"%K: {stoch['k'].iloc[-1]:.2f}")
    """
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()

    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period, min_periods=d_period).mean()

    return pd.DataFrame({
        "k": k,
        "d": d
    })


def calculate_momentum(
    prices: Union[pd.Series, np.ndarray],
    period: int = 10
) -> pd.Series:
    """
    Calculate Momentum indicator.

    Momentum is the rate of acceleration of a security's price or volume.
    It compares the current price to a previous price from a selected
    number of periods ago.

    Args:
        prices: Price series
        period: Lookback period (default: 10)

    Returns:
        Series with momentum values

    Example:
        >>> mom = calculate_momentum(data["close"], period=10)
        >>> print(f"Momentum: {mom.iloc[-1]:.2f}")
    """
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)

    return prices.diff(period)


def calculate_roc(
    prices: Union[pd.Series, np.ndarray],
    period: int = 10
) -> pd.Series:
    """
    Calculate Rate of Change (ROC).

    ROC is a momentum oscillator that measures the percentage change
    between the current price and the price n periods ago.

    Args:
        prices: Price series
        period: Lookback period (default: 10)

    Returns:
        Series with ROC values (as percentage)

    Example:
        >>> roc = calculate_roc(data["close"], period=10)
        >>> print(f"ROC: {roc.iloc[-1]:.2f}%")
    """
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)

    roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
    return roc
