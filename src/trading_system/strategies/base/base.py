"""
Base strategy classes.

Provides abstract interfaces for trading strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class SignalType(Enum):
    """Trading signal types."""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class Signal:
    """Trading signal representation."""
    date: pd.Timestamp
    type: SignalType
    price: float
    quantity: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, int):
            self.type = SignalType(self.type)


@dataclass
class StrategyConfig:
    """Base configuration for strategies."""
    name: str = "BaseStrategy"
    description: str = ""

    def validate(self) -> bool:
        """Validate configuration parameters."""
        return True


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.

    All strategies should inherit from this class and implement
    the required methods.

    Args:
        config: Strategy configuration
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()
        self.name = self.config.name
        self._indicators: Dict[str, pd.Series] = {}
        self._signals: List[Signal] = []

    @property
    @abstractmethod
    def required_columns(self) -> List[str]:
        """Columns required in input DataFrame."""
        pass

    @property
    def required_indicators(self) -> List[str]:
        """Indicators required to be precomputed."""
        return []

    def validate_data(self, data: pd.DataFrame) -> None:
        """
        Validate input data has required columns.

        Args:
            data: Input OHLCV data

        Raises:
            ValueError: If required columns are missing
        """
        missing = set(self.required_columns) - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if len(data) < self.min_periods:
            raise ValueError(
                f"Insufficient data: need at least {self.min_periods} periods"
            )

    @property
    def min_periods(self) -> int:
        """Minimum periods required for the strategy."""
        return 20

    def generate_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Generate trading signals.

        Args:
            data: OHLCV data

        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        self.validate_data(data)
        self._indicators = {}
        self._signals = []

        signals = self._compute_signals(data)

        if len(signals) != len(data):
            raise ValueError(
                f"Signal length {len(signals)} != data length {len(data)}"
            )

        valid_signals = {1, 0, -1}
        if not set(signals).issubset(valid_signals):
            raise ValueError(f"Invalid signal values: {set(signals) - valid_signals}")

        return np.array(signals)

    @abstractmethod
    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute trading signals.

        Must be implemented by subclasses.

        Args:
            data: OHLCV data

        Returns:
            Array of signals
        """
        pass

    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        if hasattr(self.config, "__dict__"):
            return {
                k: v for k, v in self.config.__dict__.items()
                if not k.startswith("_")
            }
        return {}

    def get_indicator(self, name: str) -> Optional[pd.Series]:
        """Get computed indicator by name."""
        return self._indicators.get(name)

    def get_signals(self) -> List[Signal]:
        """Get list of trading signals."""
        return self._signals.copy()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.get_parameters()})"
