"""
Statistical Arbitrage strategies module.

Implements pairs trading and mean reversion strategies based on
cointegration and statistical properties of securities.
"""

from trading_system.strategies.arbitrage.pairs_trading_strategy import (
    PairsTradingStrategy,
    PairsTradingConfig,
)
from trading_system.strategies.arbitrage.statistical_arbitrage import (
    StatisticalArbitrageStrategy,
    StatisticalArbitrageConfig,
)

__all__ = [
    "PairsTradingStrategy",
    "PairsTradingConfig",
    "StatisticalArbitrageStrategy",
    "StatisticalArbitrageConfig",
]
