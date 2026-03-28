"""
Trend Classifier Strategy.

Implements a simple trend classification strategy using moving averages.
Classifies market into uptrend, downtrend, or ranging states.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import numpy as np
import pandas as pd

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig
from trading_system.strategies.indicators import calculate_sma, calculate_ema


class TrendType(Enum):
    """Market trend types."""
    UPTREND = 1
    DOWNTREND = -1
    RANGING = 0


@dataclass
class TrendClassifierConfig(StrategyConfig):
    """Configuration for Trend Classifier strategy."""
    name: str = "TrendClassifierStrategy"
    description: str = "SMA/EMA crossover trend classification strategy"
    fast_period: int = 10
    slow_period: int = 30
    signal_period: int = 5
    uptrend_threshold: float = 0.02
    downtrend_threshold: float = -0.02
    require_confirmation: bool = True

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()

    def validate(self) -> bool:
        """Validate trend classifier parameters."""
        if not 2 <= self.fast_period <= 100:
            raise ValueError("Fast period must be between 2 and 100")
        if not 5 <= self.slow_period <= 500:
            raise ValueError("Slow period must be between 5 and 500")
        if self.fast_period >= self.slow_period:
            raise ValueError("Fast period must be less than slow period")
        if not 1 <= self.signal_period <= 50:
            raise ValueError("Signal period must be between 1 and 50")
        if not -1 <= self.uptrend_threshold <= 1:
            raise ValueError("Uptrend threshold must be between -1 and 1")
        if not -1 <= self.downtrend_threshold <= 1:
            raise ValueError("Downtrend threshold must be between -1 and 1")
        if self.uptrend_threshold <= self.downtrend_threshold:
            raise ValueError("Uptrend threshold must be greater than downtrend threshold")
        return True


class TrendClassifierStrategy(BaseStrategy):
    """
    Trend Classifier Strategy.

    Uses SMA/EMA crossovers to classify market into three states:
    - UPTREND: Fast MA above slow MA with confirmed momentum
    - DOWNTREND: Fast MA below slow MA with confirmed momentum
    - RANGING: Price oscillating without clear direction

    Generates buy signals in uptrends and sell signals in downtrends.
    Can optionally require multiple confirmation bars before signaling.

    Args:
        config: Strategy configuration

    Example:
        >>> config = TrendClassifierConfig(
        ...     fast_period=10,
        ...     slow_period=30,
        ...     uptrend_threshold=0.02
        ... )
        >>> strategy = TrendClassifierStrategy(config)
        >>> signals = strategy.generate_signals(data)
        >>> trend = strategy.get_current_trend(data)
        >>> print(f"Current trend: {trend.name}")
    """

    def __init__(self, config: Optional[TrendClassifierConfig] = None):
        if config is None:
            config = TrendClassifierConfig()
        config.validate()
        super().__init__(config)
        self.fast_period = config.fast_period
        self.slow_period = config.slow_period
        self.signal_period = config.signal_period
        self.uptrend_threshold = config.uptrend_threshold
        self.downtrend_threshold = config.downtrend_threshold
        self.require_confirmation = config.require_confirmation

    @property
    def required_columns(self) -> List[str]:
        """Required columns in input DataFrame."""
        return ["close"]

    @property
    def min_periods(self) -> int:
        """Minimum periods required."""
        return self.slow_period + self.signal_period

    def get_current_trend(self, data: pd.DataFrame) -> TrendType:
        """
        Get the current trend classification.

        Args:
            data: OHLCV data

        Returns:
            Current trend type
        """
        close = data["close"]
        
        fast_ma = calculate_sma(close, period=self.fast_period)
        slow_ma = calculate_sma(close, period=self.slow_period)
        
        ma_diff = (fast_ma - slow_ma) / slow_ma
        recent_diff = ma_diff.iloc[-self.signal_period:].mean()
        
        if recent_diff > self.uptrend_threshold:
            return TrendType.UPTREND
        elif recent_diff < self.downtrend_threshold:
            return TrendType.DOWNTREND
        else:
            return TrendType.RANGING

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute trend-based trading signals.

        Args:
            data: OHLCV data

        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        close = data["close"]
        
        fast_ma = calculate_sma(close, period=self.fast_period)
        slow_ma = calculate_sma(close, period=self.slow_period)
        signal_ma = calculate_ema(close, period=self.signal_period)
        
        self._indicators["fast_ma"] = fast_ma
        self._indicators["slow_ma"] = slow_ma
        self._indicators["signal_ma"] = signal_ma
        
        ma_diff = (fast_ma - slow_ma) / slow_ma
        self._indicators["ma_diff"] = ma_diff
        
        price_momentum = close.pct_change(periods=self.signal_period)
        self._indicators["momentum"] = price_momentum
        
        signals = np.zeros(len(data))
        
        in_position = False
        uptrend_bars = 0
        downtrend_bars = 0
        min_confirmation = self.signal_period
        
        for i in range(self.slow_period + self.signal_period, len(data)):
            current_diff = ma_diff.iloc[i]
            current_momentum = price_momentum.iloc[i]
            current_price = close.iloc[i]
            
            if not in_position:
                if current_diff > self.uptrend_threshold:
                    if self.require_confirmation:
                        uptrend_bars += 1
                        if uptrend_bars >= min_confirmation:
                            signals[i] = 1
                            in_position = True
                            uptrend_bars = 0
                    else:
                        signals[i] = 1
                        in_position = True
                    downtrend_bars = 0
                else:
                    uptrend_bars = 0
            else:
                if current_diff < self.downtrend_threshold:
                    if self.require_confirmation:
                        downtrend_bars += 1
                        if downtrend_bars >= min_confirmation:
                            signals[i] = -1
                            in_position = False
                            downtrend_bars = 0
                    else:
                        signals[i] = -1
                        in_position = False
                    uptrend_bars = 0
                else:
                    downtrend_bars = 0
                    
                    if self.require_confirmation and \
                       current_diff < self.uptrend_threshold * 0.5:
                        signals[i] = -1
                        in_position = False

        return signals


class AdaptiveTrendStrategy(BaseStrategy):
    """
    Adaptive Trend Strategy.

    An enhanced version of TrendClassifierStrategy that adapts
    to different market conditions by adjusting thresholds
    based on volatility.

    Args:
        fast_period: Fast MA period (default: 10)
        slow_period: Slow MA period (default: 30)
        volatility_lookback: Lookback period for volatility (default: 20)
        min_threshold: Minimum trend threshold (default: 0.01)
        max_threshold: Maximum trend threshold (default: 0.05)
    """

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
        volatility_lookback: int = 20,
        min_threshold: float = 0.01,
        max_threshold: float = 0.05
    ):
        config = TrendClassifierConfig(
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=5,
            uptrend_threshold=max_threshold,
            downtrend_threshold=min_threshold
        )
        super().__init__(config)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.volatility_lookback = volatility_lookback
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold

    @property
    def required_columns(self) -> List[str]:
        return ["close"]

    @property
    def min_periods(self) -> int:
        return max(
            self.config.slow_period + self.config.signal_period,
            self.volatility_lookback
        )

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute adaptive trend signals.
        
        Adjusts thresholds based on recent volatility.
        """
        close = data["close"]
        
        returns = close.pct_change()
        volatility = returns.rolling(window=self.volatility_lookback).std()
        
        normalized_vol = volatility / volatility.rolling(window=50).mean()
        normalized_vol = normalized_vol.clip(0.5, 2.0)
        
        adaptive_up = self.min_threshold + \
            (self.max_threshold - self.min_threshold) * normalized_vol
        adaptive_down = -adaptive_up
        
        fast_ma = calculate_sma(close, period=self.config.fast_period)
        slow_ma = calculate_sma(close, period=self.config.slow_period)
        
        ma_diff = (fast_ma - slow_ma) / slow_ma
        
        self._indicators["ma_diff"] = ma_diff
        self._indicators["volatility"] = volatility
        self._indicators["adaptive_up"] = adaptive_up
        self._indicators["adaptive_down"] = adaptive_down

        signals = np.zeros(len(data))
        
        in_position = False
        
        for i in range(self.min_periods, len(data)):
            current_diff = ma_diff.iloc[i]
            current_up = adaptive_up.iloc[i]
            current_down = adaptive_down.iloc[i]
            
            if not in_position:
                if current_diff > current_up:
                    signals[i] = 1
                    in_position = True
            else:
                if current_diff < current_down:
                    signals[i] = -1
                    in_position = False

        return signals
