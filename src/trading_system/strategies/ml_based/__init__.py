"""
ML-based trading strategies module.

Provides machine learning-based trading strategy implementations.
"""

from trading_system.strategies.ml_based.trend_classifier_strategy import (
    TrendClassifierStrategy,
    TrendClassifierConfig,
    TrendType,
)
from trading_system.strategies.ml_based.momentum_ml_strategy import (
    MomentumMLStrategy,
    MomentumMLConfig,
)

__all__ = [
    "TrendClassifierStrategy",
    "TrendClassifierConfig",
    "TrendType",
    "MomentumMLStrategy",
    "MomentumMLConfig",
]
