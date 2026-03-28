"""
Backtesting module.
"""

from trading_system.backtesting.engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
    Trade,
)
from trading_system.backtesting.metrics import (
    AdvancedMetrics,
    calculate_advanced_metrics,
)
from trading_system.backtesting.reporting import (
    ReportGenerator,
    ReportConfig,
    ChartConfig,
)

__all__ = [
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "Trade",
    "AdvancedMetrics",
    "calculate_advanced_metrics",
    "ReportGenerator",
    "ReportConfig",
    "ChartConfig",
]
