"""
Mean reversion strategies module.

Provides strategies that exploit the tendency of prices to revert
to their mean or average value over time.
"""

from trading_system.strategies.mean_reversion.bollinger_strategy import (
    BollingerBandsStrategy,
    BollingerBandsStrategyConfig,
)
from trading_system.strategies.mean_reversion.mean_reversion_strategy import (
    MeanReversionStrategy,
    MeanReversionConfig,
)

__all__ = [
    "BollingerBandsStrategy",
    "BollingerBandsStrategyConfig",
    "MeanReversionStrategy",
    "MeanReversionConfig",
]
