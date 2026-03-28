"""
Optimization module for trading strategies.

Provides functionality for parameter optimization and walk-forward analysis
to find optimal strategy parameters and validate robustness.

Example:
    >>> from trading_system.optimization import StrategyOptimizer
    >>> optimizer = StrategyOptimizer()
    >>> result = optimizer.optimize(MyStrategy, data, param_grid)
    >>> print(f"Best params: {result.best_params}")
"""

from trading_system.optimization.optimizer import (
    OptimizationResult,
    StrategyOptimizer,
    OptimizationConfig,
    MetricType,
)
from trading_system.optimization.walk_forward import (
    WalkForwardResult,
    WalkForwardOptimizer,
    WalkForwardConfig,
    WindowType,
)

__all__ = [
    "OptimizationResult",
    "StrategyOptimizer",
    "OptimizationConfig",
    "MetricType",
    "WalkForwardResult",
    "WalkForwardOptimizer",
    "WalkForwardConfig",
    "WindowType",
]
