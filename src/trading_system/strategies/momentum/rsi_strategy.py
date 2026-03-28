"""
RSI Momentum Strategy.

Implements a trading strategy based on Relative Strength Index (RSI).
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig
from trading_system.strategies.indicators.momentum import calculate_rsi


@dataclass
class RSIStrategyConfig(StrategyConfig):
    """Configuration for RSI strategy."""
    name: str = "RSIStrategy"
    description: str = "RSI-based momentum strategy"
    period: int = 14
    overbought: float = 70.0
    oversold: float = 30.0
    exit_overbought: bool = True
    exit_oversold: bool = True

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()

    def validate(self) -> bool:
        """Validate RSI parameters."""
        if not 2 <= self.period <= 200:
            raise ValueError("Period must be between 2 and 200")
        if not 50 <= self.overbought <= 100:
            raise ValueError("Overbought must be between 50 and 100")
        if not 0 <= self.oversold <= 50:
            raise ValueError("Oversold must be between 0 and 50")
        if self.overbought <= self.oversold:
            raise ValueError("Overbought must be greater than oversold")
        return True


class RSIStrategy(BaseStrategy):
    """
    RSI Momentum Strategy.

    Generates buy signals when RSI enters oversold territory and sell
    signals when RSI enters overbought territory.

    Args:
        config: Strategy configuration

    Example:
        >>> config = RSIStrategyConfig(period=14, overbought=70, oversold=30)
        >>> strategy = RSIStrategy(config)
        >>> signals = strategy.generate_signals(data)
        >>> print(f"Buy signals: {(signals == 1).sum()}")
    """

    def __init__(self, config: Optional[RSIStrategyConfig] = None):
        if config is None:
            config = RSIStrategyConfig()
        config.validate()
        super().__init__(config)
        self.period = config.period
        self.overbought = config.overbought
        self.oversold = config.oversold
        self.exit_overbought = config.exit_overbought
        self.exit_oversold = config.exit_oversold

    @property
    def required_columns(self) -> List[str]:
        """Required columns in input DataFrame."""
        return ["close"]

    @property
    def min_periods(self) -> int:
        """Minimum periods required."""
        return self.period + 1

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute RSI-based trading signals.

        Args:
            data: OHLCV data

        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        close = data["close"]
        rsi = calculate_rsi(close, period=self.period)

        self._indicators["rsi"] = rsi

        signals = np.zeros(len(data))

        in_position = False

        for i in range(self.period, len(data)):
            current_rsi = rsi.iloc[i]

            if not in_position:
                if current_rsi < self.oversold:
                    signals[i] = 1
                    in_position = True
            else:
                if self.exit_overbought and current_rsi > self.overbought:
                    signals[i] = -1
                    in_position = False
                elif not self.exit_overbought and current_rsi > 50:
                    signals[i] = -1
                    in_position = False

        return signals


class RSIConvergenceStrategy(BaseStrategy):
    """
    RSI with Price Convergence Strategy.

    A more conservative RSI strategy that requires price and RSI
    to show convergence before generating signals.

    Args:
        period: RSI period (default: 14)
        overbought: Overbought threshold (default: 70)
        oversold: Oversold threshold (default: 30)
    """

    def __init__(
        self,
        period: int = 14,
        overbought: float = 70.0,
        oversold: float = 30.0
    ):
        config = RSIStrategyConfig(
            period=period,
            overbought=overbought,
            oversold=oversold
        )
        super().__init__(config)
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    @property
    def required_columns(self) -> List[str]:
        return ["close"]

    @property
    def min_periods(self) -> int:
        return self.period + 10

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute RSI convergence signals.

        Signals are generated only when price and RSI show
        convergence (both making higher lows or higher highs).
        """
        close = data["close"]
        rsi = calculate_rsi(close, period=self.period)

        self._indicators["rsi"] = rsi

        signals = np.zeros(len(data))

        price_lows = close.rolling(window=5).min()
        price_highs = close.rolling(window=5).max()
        rsi_lows = rsi.rolling(window=5).min()
        rsi_highs = rsi.rolling(window=5).max()

        in_position = False

        for i in range(self.period + 5, len(data)):
            if not in_position:
                price_bullish = price_lows.iloc[i] > price_lows.iloc[i - 1]
                rsi_bullish = rsi_lows.iloc[i] < self.oversold and \
                              rsi_lows.iloc[i] > rsi_lows.iloc[i - 5]
                price_bearish = price_highs.iloc[i] < price_highs.iloc[i - 1]
                rsi_bearish = rsi_highs.iloc[i] > self.overbought and \
                              rsi_highs.iloc[i] < rsi_highs.iloc[i - 5]

                if rsi.iloc[i] < self.oversold and price_bullish:
                    signals[i] = 1
                    in_position = True
            else:
                if rsi.iloc[i] > self.overbought:
                    signals[i] = -1
                    in_position = False

        return signals
