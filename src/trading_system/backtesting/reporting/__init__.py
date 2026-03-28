"""
Reporting module for backtesting results.

Provides tools for generating reports and visualizations.
"""

from trading_system.backtesting.reporting.report_generator import (
    ReportGenerator,
    ReportConfig,
    ChartConfig,
)

__all__ = [
    "ReportGenerator",
    "ReportConfig",
    "ChartConfig",
]
