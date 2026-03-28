"""
Trading strategies module.

Provides various trading strategy implementations.
"""

from trading_system.strategies.base import (
    BaseStrategy,
    Signal,
    SignalType,
    StrategyConfig,
)
from trading_system.strategies.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_sma,
    calculate_ema,
    calculate_bollinger_bands,
    calculate_atr,
)
from trading_system.strategies.momentum import (
    RSIStrategy,
    MACDStrategy,
)
from trading_system.strategies.mean_reversion import (
    BollingerBandsStrategy,
    BollingerBandsStrategyConfig,
    MeanReversionStrategy,
    MeanReversionConfig,
)
from trading_system.strategies.ml_based import (
    TrendClassifierStrategy,
    TrendClassifierConfig,
    TrendType,
    MomentumMLStrategy,
    MomentumMLConfig,
)
from trading_system.strategies.arbitrage import (
    PairsTradingStrategy,
    PairsTradingConfig,
    StatisticalArbitrageStrategy,
    StatisticalArbitrageConfig,
)

__all__ = [
    "BaseStrategy",
    "Signal",
    "SignalType",
    "StrategyConfig",
    "calculate_rsi",
    "calculate_macd",
    "calculate_sma",
    "calculate_ema",
    "calculate_bollinger_bands",
    "calculate_atr",
    "RSIStrategy",
    "MACDStrategy",
    "BollingerBandsStrategy",
    "BollingerBandsStrategyConfig",
    "MeanReversionStrategy",
    "MeanReversionConfig",
    "TrendClassifierStrategy",
    "TrendClassifierConfig",
    "TrendType",
    "MomentumMLStrategy",
    "MomentumMLConfig",
    "PairsTradingStrategy",
    "PairsTradingConfig",
    "StatisticalArbitrageStrategy",
    "StatisticalArbitrageConfig",
]
