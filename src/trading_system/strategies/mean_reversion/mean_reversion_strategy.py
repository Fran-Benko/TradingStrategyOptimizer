"""
Classic Mean Reversion Strategy using Z-Score.

Implements mean reversion trading based on statistical z-score of price
deviation from a rolling mean - buying oversold conditions and selling
overbought conditions as price reverts to the mean.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig
from trading_system.strategies.indicators.trend import calculate_sma


@dataclass
class MeanReversionConfig(StrategyConfig):
    """
    Configuration for Z-Score Mean Reversion strategy.

    Attributes:
        name: Strategy name
        description: Strategy description
        lookback_period: Period for calculating rolling mean and std (default: 20)
        entry_threshold: Z-score threshold for entry (default: -2.0)
        exit_threshold: Z-score threshold for exit (default: 0.0)
        use_stochastic_entry: Use additional stochastic confirmation for entries
        use_adaptive_thresholds: Adjust thresholds based on recent volatility
        position_size: Size of each position (default: 1.0)
        max_position_hold: Maximum periods to hold position (0 = unlimited)
    """
    name: str = "MeanReversionStrategy"
    description: str = "Z-score mean reversion strategy"
    lookback_period: int = 20
    entry_threshold: float = -2.0
    exit_threshold: float = 0.0
    use_stochastic_entry: bool = False
    use_adaptive_thresholds: bool = False
    position_size: float = 1.0
    max_position_hold: int = 0

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()

    def validate(self) -> bool:
        """
        Validate mean reversion parameters.

        Returns:
            True if validation passes

        Raises:
            ValueError: If any parameter is invalid
        """
        if not 5 <= self.lookback_period <= 500:
            raise ValueError("Lookback period must be between 5 and 500")
        if not -5.0 <= self.entry_threshold <= -0.1:
            raise ValueError("Entry threshold must be between -5.0 and -0.1")
        if not -3.0 <= self.exit_threshold <= 3.0:
            raise ValueError("Exit threshold must be between -3.0 and 3.0")
        if self.entry_threshold >= self.exit_threshold:
            raise ValueError("Entry threshold must be less than exit threshold")
        if self.position_size <= 0:
            raise ValueError("Position size must be positive")
        if self.max_position_hold < 0:
            raise ValueError("Max position hold must be non-negative")
        return True


class MeanReversionStrategy(BaseStrategy):
    """
    Z-Score Mean Reversion Strategy.

    This strategy assumes that prices tend to revert to their mean over time.
    It uses statistical z-scores to identify when price has deviated significantly
    from its historical mean, expecting a reversion.

    Signal Logic:
    - Buy (1): When z-score is below entry_threshold (oversold)
    - Sell (-1): When z-score crosses above exit_threshold (mean or overbought)
    - Hold (0): Otherwise

    The z-score is calculated as: (price - rolling_mean) / rolling_std

    Args:
        config: Strategy configuration

    Attributes:
        lookback_period: Period for mean and standard deviation
        entry_threshold: Z-score level for entry signals
        exit_threshold: Z-score level for exit signals

    Example:
        >>> config = MeanReversionConfig(lookback_period=20, entry_threshold=-2.0)
        >>> strategy = MeanReversionStrategy(config)
        >>> signals = strategy.generate_signals(data)
        >>> print(f"Buy signals: {(signals == 1).sum()}")
    """

    def __init__(self, config: Optional[MeanReversionConfig] = None):
        if config is None:
            config = MeanReversionConfig()
        config.validate()
        super().__init__(config)
        self.lookback_period = config.lookback_period
        self.entry_threshold = config.entry_threshold
        self.exit_threshold = config.exit_threshold
        self.use_stochastic_entry = config.use_stochastic_entry
        self.use_adaptive_thresholds = config.use_adaptive_thresholds
        self.position_size = config.position_size
        self.max_position_hold = config.max_position_hold

    @property
    def required_columns(self) -> List[str]:
        """
        Required columns in input DataFrame.

        Returns:
            List of required column names
        """
        return ["close"]

    @property
    def min_periods(self) -> int:
        """
        Minimum periods required for calculation.

        Returns:
            Minimum number of periods needed
        """
        return self.lookback_period + 2

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute Z-Score mean reversion trading signals.

        Args:
            data: OHLCV data with 'close' column

        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        close = data["close"]

        # Calculate rolling statistics
        rolling_mean = calculate_sma(close, period=self.lookback_period)
        rolling_std = close.rolling(window=self.lookback_period, min_periods=self.lookback_period).std()

        # Calculate z-score
        z_score = (close - rolling_mean) / rolling_std

        # Handle any infinite or NaN values
        z_score = z_score.replace([np.inf, -np.inf], np.nan).fillna(0)

        # Store indicators for analysis
        self._indicators["z_score"] = z_score
        self._indicators["rolling_mean"] = rolling_mean
        self._indicators["rolling_std"] = rolling_std

        # Calculate adaptive thresholds if enabled
        if self.use_adaptive_thresholds:
            entry_threshold, exit_threshold = self._calculate_adaptive_thresholds(
                z_score, rolling_std
            )
        else:
            entry_threshold = self.entry_threshold
            exit_threshold = self.exit_threshold

        self._indicators["entry_threshold"] = entry_threshold
        self._indicators["exit_threshold"] = exit_threshold

        # Add stochastic confirmation if enabled
        if self.use_stochastic_entry:
            self._indicators["stochastic"] = self._calculate_stochastic(close)

        signals = np.zeros(len(data))

        in_position = False
        entry_bar = 0
        position_held_bars = 0

        for i in range(self.lookback_period, len(data)):
            current_z = z_score.iloc[i]

            # Check for time-based exit (max hold)
            if self.max_position_hold > 0 and in_position:
                position_held_bars = i - entry_bar

            if in_position:
                # Exit when z-score crosses above exit threshold or max hold reached
                if current_z >= exit_threshold or (
                    self.max_position_hold > 0 and position_held_bars >= self.max_position_hold
                ):
                    signals[i] = -1
                    in_position = False
                    position_held_bars = 0
            else:
                # Entry when z-score is below entry threshold (with optional stochastic)
                if self._should_enter(current_z, i, close):
                    signals[i] = 1
                    in_position = True
                    entry_bar = i

        return signals

    def _should_enter(self, z_score: float, index: int, close: pd.Series) -> bool:
        """
        Determine if we should enter a position.

        Args:
            z_score: Current z-score value
            index: Current bar index
            close: Close price series

        Returns:
            True if should enter, False otherwise
        """
        # Check z-score threshold
        if z_score >= self.entry_threshold:
            return False

        # Check stochastic confirmation if enabled
        if self.use_stochastic_entry:
            stochastic = self._indicators.get("stochastic")
            if stochastic is not None:
                # Stochastic below 20 indicates oversold
                return stochastic.iloc[index] < 20

        return True

    def _calculate_adaptive_thresholds(
        self,
        z_score: pd.Series,
        rolling_std: pd.Series
    ) -> tuple:
        """
        Calculate adaptive thresholds based on recent volatility.

        Args:
            z_score: Z-score series
            rolling_std: Rolling standard deviation series

        Returns:
            Tuple of (entry_threshold, exit_threshold)
        """
        # Calculate recent volatility percentile
        recent_vol = rolling_std.iloc[-20:].mean() if len(rolling_std) >= 20 else rolling_std.mean()
        baseline_vol = rolling_std.mean()

        volatility_ratio = recent_vol / baseline_vol if baseline_vol > 0 else 1.0

        # Adjust thresholds based on volatility
        # Higher volatility = wider thresholds
        adjustment_factor = max(0.5, min(2.0, volatility_ratio))

        entry = self.entry_threshold * adjustment_factor
        exit_threshold = self.exit_threshold * adjustment_factor

        return entry, exit_threshold

    def _calculate_stochastic(self, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Stochastic Oscillator for additional confirmation.

        Args:
            close: Close price series
            period: Stochastic period

        Returns:
            Stochastic %K series
        """
        low_min = close.rolling(window=period).min()
        high_max = close.rolling(window=period).max()

        diff = high_max - low_min
        stochastic = 100 * (close - low_min) / diff.where(diff > 0, 1)
        return stochastic.clip(0, 100).fillna(50)

    def get_parameters(self) -> dict:
        """
        Get strategy parameters.

        Returns:
            Dictionary of strategy parameters
        """
        return {
            "lookback_period": self.lookback_period,
            "entry_threshold": self.entry_threshold,
            "exit_threshold": self.exit_threshold,
            "use_stochastic_entry": self.use_stochastic_entry,
            "use_adaptive_thresholds": self.use_adaptive_thresholds,
            "position_size": self.position_size,
            "max_position_hold": self.max_position_hold,
        }
