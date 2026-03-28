"""
MACD Momentum Strategy.

Implements a trading strategy based on MACD (Moving Average Convergence Divergence).
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig
from trading_system.strategies.indicators.momentum import calculate_macd


@dataclass
class MACDStrategyConfig(StrategyConfig):
    """Configuration for MACD strategy."""
    name: str = "MACDStrategy"
    description: str = "MACD crossover strategy"
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    histogram_threshold: float = 0.0

    def __post_init__(self) -> None:
        """Validate parameters after initialization."""
        self.validate()

    def validate(self) -> bool:
        """Validate MACD parameters."""
        if not 1 <= self.fast_period < self.slow_period:
            raise ValueError("Fast period must be less than slow period")
        if not 1 <= self.signal_period <= self.slow_period:
            raise ValueError("Signal period must be valid")
        return True


class MACDStrategy(BaseStrategy):
    """
    MACD Crossover Strategy.

    Generates buy signals when MACD crosses above signal line
    and sell signals when MACD crosses below signal line.

    Args:
        config: Strategy configuration

    Example:
        >>> config = MACDStrategyConfig()
        >>> strategy = MACDStrategy(config)
        >>> signals = strategy.generate_signals(data)
        >>> print(f"Total signals: {(signals != 0).sum()}")
    """

    def __init__(self, config: Optional[MACDStrategyConfig] = None):
        if config is None:
            config = MACDStrategyConfig()
        super().__init__(config)
        self.fast_period = config.fast_period
        self.slow_period = config.slow_period
        self.signal_period = config.signal_period
        self.histogram_threshold = config.histogram_threshold

    @property
    def required_columns(self) -> List[str]:
        return ["close"]

    @property
    def min_periods(self) -> int:
        return self.slow_period + self.signal_period

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute MACD crossover signals.

        Args:
            data: OHLCV data

        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        close = data["close"]
        macd_data = calculate_macd(
            close,
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            signal_period=self.signal_period
        )

        macd_line = macd_data["macd"]
        signal_line = macd_data["signal"]
        histogram = macd_data["histogram"]

        self._indicators["macd"] = macd_line
        self._indicators["signal"] = signal_line
        self._indicators["histogram"] = histogram

        signals = np.zeros(len(data))

        macd_above = macd_line > signal_line
        macd_below = macd_line < signal_line

        crossover_up = (macd_above.values[1:] & ~macd_above.values[:-1])
        crossover_down = (macd_below.values[1:] & ~macd_below.values[:-1])

        histogram_positive = histogram > self.histogram_threshold

        for i in range(1, len(data)):
            if crossover_up[i - 1] and histogram_positive.iloc[i]:
                signals[i] = 1
            elif crossover_down[i - 1]:
                signals[i] = -1

        return signals


class MACDHistogramStrategy(BaseStrategy):
    """
    MACD Histogram Strategy.

    Generates signals based on MACD histogram direction changes
    and zero line crossovers.

    Args:
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line period (default: 9)
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        config = MACDStrategyConfig(
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period
        )
        super().__init__(config)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    @property
    def required_columns(self) -> List[str]:
        return ["close"]

    @property
    def min_periods(self) -> int:
        return self.slow_period + self.signal_period

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """Compute MACD histogram signals."""
        close = data["close"]
        macd_data = calculate_macd(
            close,
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            signal_period=self.signal_period
        )

        histogram = macd_data["histogram"]

        self._indicators["histogram"] = histogram

        signals = np.zeros(len(data))

        histogram_above_zero = histogram > 0
        histogram_positive_slope = histogram.diff() > 0

        in_position = False

        for i in range(2, len(data)):
            if not in_position:
                if (histogram_above_zero.iloc[i] and
                    histogram_positive_slope.iloc[i] and
                    histogram_positive_slope.iloc[i - 1]):
                    signals[i] = 1
                    in_position = True
            else:
                if not histogram_above_zero.iloc[i]:
                    signals[i] = -1
                    in_position = False

        return signals
