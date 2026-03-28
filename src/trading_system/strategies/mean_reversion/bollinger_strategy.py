"""
Bollinger Bands Mean Reversion Strategy.

Implements mean reversion trading using Bollinger Bands - buying when price
touches the lower band and selling when price reverts to the middle or upper band.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig
from trading_system.strategies.indicators.trend import calculate_bollinger_bands


@dataclass
class BollingerBandsStrategyConfig(StrategyConfig):
    """
    Configuration for Bollinger Bands mean reversion strategy.

    Attributes:
        name: Strategy name
        description: Strategy description
        period: Moving average period for Bollinger Bands (default: 20)
        num_std: Number of standard deviations for bands (default: 2.0)
        exit_mode: Exit mode - 'middle' exits at middle band, 'upper' at upper band
        position_size: Size of each position (default: 1.0)
        use_trailing_stop: Whether to use trailing stop for exits
        trailing_stop_pct: Trailing stop percentage when enabled
    """
    name: str = "BollingerBandsStrategy"
    description: str = "Bollinger Bands mean reversion strategy"
    period: int = 20
    num_std: float = 2.0
    exit_mode: str = "middle"
    position_size: float = 1.0
    use_trailing_stop: bool = False
    trailing_stop_pct: float = 0.02

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()

    def validate(self) -> bool:
        """
        Validate Bollinger Bands parameters.

        Returns:
            True if validation passes

        Raises:
            ValueError: If any parameter is invalid
        """
        if not 5 <= self.period <= 200:
            raise ValueError("Period must be between 5 and 200")
        if not 0.5 <= self.num_std <= 4.0:
            raise ValueError("Num_std must be between 0.5 and 4.0")
        if self.exit_mode not in ("middle", "upper"):
            raise ValueError("Exit mode must be 'middle' or 'upper'")
        if self.position_size <= 0:
            raise ValueError("Position size must be positive")
        if self.use_trailing_stop:
            if not 0.001 <= self.trailing_stop_pct <= 0.5:
                raise ValueError("Trailing stop percentage must be between 0.001 and 0.5")
        return True


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Mean Reversion Strategy.

    Buys when price touches or crosses below the lower Bollinger Band, expecting
    price to revert to the mean (middle band). Exits when price reaches the
    middle band or upper band depending on exit_mode setting.

    The strategy assumes that price deviations from the mean are temporary and
    that prices will eventually revert to their average value.

    Args:
        config: Strategy configuration

    Attributes:
        period: Bollinger Bands period
        num_std: Number of standard deviations
        exit_mode: Where to exit positions

    Example:
        >>> config = BollingerBandsStrategyConfig(period=20, num_std=2.0)
        >>> strategy = BollingerBandsStrategy(config)
        >>> signals = strategy.generate_signals(data)
        >>> print(f"Buy signals: {(signals == 1).sum()}")
    """

    def __init__(self, config: Optional[BollingerBandsStrategyConfig] = None):
        if config is None:
            config = BollingerBandsStrategyConfig()
        config.validate()
        super().__init__(config)
        self.period = config.period
        self.num_std = config.num_std
        self.exit_mode = config.exit_mode
        self.position_size = config.position_size
        self.use_trailing_stop = config.use_trailing_stop
        self.trailing_stop_pct = config.trailing_stop_pct

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
        return self.period + 2

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute Bollinger Bands mean reversion trading signals.

        Signal logic:
        - Buy (1): When price touches or crosses below lower band
        - Sell (-1): When price reaches middle/upper band or trailing stop hit
        - Hold (0): Otherwise

        Args:
            data: OHLCV data with 'close' column

        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        close = data["close"]

        # Calculate Bollinger Bands
        bb = calculate_bollinger_bands(close, period=self.period, num_std=self.num_std)
        upper_band = bb["upper"]
        middle_band = bb["middle"]
        lower_band = bb["lower"]

        # Store indicators for analysis
        self._indicators["upper_band"] = upper_band
        self._indicators["middle_band"] = middle_band
        self._indicators["lower_band"] = lower_band
        self._indicators["bandwidth"] = (upper_band - lower_band) / middle_band

        signals = np.zeros(len(data))

        in_position = False
        entry_price = 0.0
        highest_price_since_entry = 0.0

        for i in range(self.period, len(data)):
            current_price = close.iloc[i]
            current_lower = lower_band.iloc[i]
            current_middle = middle_band.iloc[i]
            current_upper = upper_band.iloc[i]

            if in_position:
                # Update highest price for trailing stop
                if self.use_trailing_stop:
                    highest_price_since_entry = max(highest_price_since_entry, current_price)

                # Check exit conditions
                if self._should_exit(
                    current_price,
                    current_middle,
                    current_upper,
                    highest_price_since_entry
                ):
                    signals[i] = -1
                    in_position = False
                    highest_price_since_entry = 0.0
            else:
                # Check entry conditions - price at or below lower band
                if current_price <= current_lower:
                    signals[i] = 1
                    in_position = True
                    entry_price = current_price
                    highest_price_since_entry = current_price

        return signals

    def _should_exit(
        self,
        current_price: float,
        middle_band: float,
        upper_band: float,
        highest_price: float
    ) -> bool:
        """
        Determine if we should exit the current position.

        Args:
            current_price: Current close price
            middle_band: Current middle Bollinger Band
            upper_band: Current upper Bollinger Band
            highest_price: Highest price since entry

        Returns:
            True if should exit, False otherwise
        """
        # Check trailing stop first if enabled
        if self.use_trailing_stop:
            trailing_stop_price = highest_price * (1 - self.trailing_stop_pct)
            if current_price <= trailing_stop_price:
                return True

        # Check band-based exit
        if self.exit_mode == "middle":
            return current_price >= middle_band
        else:  # exit_mode == "upper"
            return current_price >= upper_band

    def get_parameters(self) -> dict:
        """
        Get strategy parameters.

        Returns:
            Dictionary of strategy parameters
        """
        return {
            "period": self.period,
            "num_std": self.num_std,
            "exit_mode": self.exit_mode,
            "position_size": self.position_size,
            "use_trailing_stop": self.use_trailing_stop,
            "trailing_stop_pct": self.trailing_stop_pct if self.use_trailing_stop else None,
        }
