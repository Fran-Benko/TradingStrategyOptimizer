"""
Strategy parameter optimizer.

Provides grid search optimization with support for multiple metrics,
cross-validation, and memory-efficient processing for large parameter grids.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from itertools import product
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import numpy as np
import pandas as pd

from trading_system.backtesting.engine import BacktestConfig, BacktestEngine, BacktestResult
from trading_system.strategies.base.base import BaseStrategy, StrategyConfig


class MetricType(Enum):
    """Supported optimization metrics."""
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    TOTAL_RETURN = "total_return"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    CALMAR_RATIO = "calmar_ratio"
    MAX_DRAWDOWN = "max_drawdown"  # Minimized
    NEGATIVE_DRAWDOWN = "max_drawdown_pct"  # Minimized


@dataclass
class OptimizationConfig:
    """Configuration for optimization runs."""
    metric: MetricType = MetricType.SHARPE_RATIO
    maximize: bool = True  # True for ratios, False for drawdown
    cv_folds: int = 1  # Number of cross-validation folds
    cv_window_size: Optional[int] = None  # Window size per fold
    min_trades_per_fold: int = 10  # Minimum trades required per fold
    n_jobs: int = 1  # Parallel jobs (1 = sequential)
    verbose: bool = True  # Progress logging
    progress_interval: int = 10  # Log progress every N combinations
    memory_efficient: bool = True  # Store only summary metrics
    seed: Optional[int] = None  # Random seed for reproducibility

    def validate(self) -> bool:
        """Validate optimization configuration."""
        if self.cv_folds < 1:
            raise ValueError("cv_folds must be >= 1")
        if self.cv_folds > 1 and self.cv_window_size is None:
            raise ValueError("cv_window_size required for cv_folds > 1")
        if self.min_trades_per_fold < 1:
            raise ValueError("min_trades_per_fold must be >= 1")
        if self.n_jobs < 1:
            raise ValueError("n_jobs must be >= 1")
        return True


@dataclass
class OptimizationResult:
    """
    Results from a parameter optimization run.

    Attributes:
        best_params: Dictionary of optimal parameters
        best_score: Best metric value achieved
        best_metric: Metric type used for optimization
        all_results: DataFrame with all parameter combinations and metrics
        optimization_time: Time taken for optimization in seconds
        validation_results: Cross-validation results if cv_folds > 1
        total_combinations: Total number of parameter combinations tested
        valid_combinations: Number of combinations with sufficient trades
    """
    best_params: Dict[str, Any]
    best_score: float
    best_metric: MetricType
    all_results: pd.DataFrame
    optimization_time: float
    validation_results: Optional[pd.DataFrame] = None
    total_combinations: int = 0
    valid_combinations: int = 0

    def summary(self) -> str:
        """Generate summary string of optimization results."""
        validation_info = ""
        if self.validation_results is not None:
            cv_mean = self.validation_results["cv_score"].mean()
            cv_std = self.validation_results["cv_score"].std()
            validation_info = f"\n  CV Score: {cv_mean:.4f} (+/- {cv_std:.4f})"

        return f"""
=== Optimization Results ===
Metric: {self.best_metric.value}
Best Score: {self.best_score:.4f}
Best Parameters: {self.best_params}

Statistics:
  Total Combinations: {self.total_combinations}
  Valid Combinations: {self.valid_combinations}
  Optimization Time: {self.optimization_time:.2f}s{validation_info}
"""

    def top_n(self, n: int = 10) -> pd.DataFrame:
        """Return top N parameter combinations."""
        if self.best_metric in (MetricType.MAX_DRAWDOWN, MetricType.NEGATIVE_DRAWDOWN):
            # For minimized metrics, sort ascending
            return self.all_results.nsmallest(n, self.best_metric.value)
        return self.all_results.nlargest(n, self.best_metric.value)


class StrategyOptimizer:
    """
    Grid search optimizer for strategy parameters.

    Performs exhaustive parameter search over a defined grid,
    evaluating each combination using the specified metric.

    Args:
        backtest_config: Configuration for backtesting
        optimization_config: Configuration for optimization

    Example:
        >>> optimizer = StrategyOptimizer()
        >>> param_grid = {
        ...     'rsi_period': [10, 14, 20],
        ...     'overbought': [70, 80],
        ...     'oversold': [20, 30]
        ... }
        >>> result = optimizer.optimize(RSIStrategy, data, param_grid)
        >>> print(result.best_params)
    """

    def __init__(
        self,
        backtest_config: Optional[BacktestConfig] = None,
        optimization_config: Optional[OptimizationConfig] = None
    ):
        self.backtest_config = backtest_config or BacktestConfig()
        self.optimization_config = optimization_config or OptimizationConfig()
        self.optimization_config.validate()
        self._backtest_engine = BacktestEngine(self.backtest_config)

    def optimize(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        symbol: str = "OPTIMIZE",
        metric: Optional[MetricType] = None,
    ) -> OptimizationResult:
        """
        Optimize strategy parameters using grid search.

        Args:
            strategy_class: Strategy class to optimize
            data: Historical OHLCV data
            param_grid: Dictionary of parameter names to value lists
            symbol: Symbol being traded
            metric: Override metric (uses config default if None)

        Returns:
            OptimizationResult with best parameters and all results

        Raises:
            ValueError: If param_grid is empty or no valid combinations found
        """
        if not param_grid:
            raise ValueError("param_grid cannot be empty")

        metric = metric or self.optimization_config.metric
        start_time = datetime.now()

        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        total_combinations = len(combinations)

        if total_combinations == 0:
            raise ValueError("No parameter combinations to test")

        # Pre-allocate results storage
        results_list: List[Dict[str, Any]] = []
        valid_count = 0

        # Set random seed if specified
        if self.optimization_config.seed is not None:
            np.random.seed(self.optimization_config.seed)

        # Cross-validation setup
        cv_results: Optional[List[Dict[str, Any]]] = None
        if self.optimization_config.cv_folds > 1:
            cv_results = []

        # Grid search
        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))

            # Skip invalid parameter combinations early
            try:
                if not self._validate_params(strategy_class, params):
                    results_list.append({
                        **{"params": params},
                        **{m.value: np.nan for m in MetricType},
                        "valid": False,
                        "reason": "validation_failed"
                    })
                    continue
            except Exception as e:
                results_list.append({
                    **{"params": params},
                    **{m.value: np.nan for m in MetricType},
                    "valid": False,
                    "reason": str(e)
                })
                continue

            # Run optimization (with or without CV)
            if self.optimization_config.cv_folds > 1:
                metrics, fold_results = self._optimize_with_cv(
                    strategy_class, data, params, symbol, metric
                )
                if fold_results:
                    cv_results.extend(fold_results)
            else:
                metrics = self._evaluate_params(
                    strategy_class, data, params, symbol
                )

            # Check if result is valid
            if metrics is not None and not np.isnan(metrics[metric.value]):
                valid_count += 1
                result_dict = {"params": params, **metrics, "valid": True, "reason": ""}
            else:
                result_dict = {
                    "params": params,
                    **{m.value: np.nan for m in MetricType},
                    "valid": False,
                    "reason": "insufficient_trades"
                }

            results_list.append(result_dict)

            # Progress logging
            if self.optimization_config.verbose:
                self._log_progress(i + 1, total_combinations, params, metrics, metric)

        # Convert to DataFrame
        all_results = pd.DataFrame(results_list)

        # Find best parameters
        best_row = self._find_best_params(all_results, metric)

        # Calculate optimization time
        optimization_time = (datetime.now() - start_time).total_seconds()

        # Prepare validation results
        validation_df = None
        if cv_results:
            validation_df = pd.DataFrame(cv_results)

        return OptimizationResult(
            best_params=best_row["params"] if best_row is not None else {},
            best_score=best_row[metric.value] if best_row is not None else np.nan,
            best_metric=metric,
            all_results=all_results,
            optimization_time=optimization_time,
            validation_results=validation_df,
            total_combinations=total_combinations,
            valid_combinations=valid_count
        )

    def _validate_params(
        self,
        strategy_class: Type[BaseStrategy],
        params: Dict[str, Any]
    ) -> bool:
        """Validate that parameters are valid for the strategy."""
        # Create strategy instance to check validation
        try:
            config = self._create_strategy_config(strategy_class, params)
            strategy = strategy_class(config)
            return True
        except (ValueError, TypeError):
            return False

    def _create_strategy_config(
        self,
        strategy_class: Type[BaseStrategy],
        params: Dict[str, Any]
    ) -> StrategyConfig:
        """Create strategy config from parameters."""
        # Default to StrategyConfig with name
        config = StrategyConfig(name=strategy_class.__name__)

        # Merge params into config
        if hasattr(config, "__dict__"):
            for key, value in params.items():
                if not key.startswith("_"):
                    setattr(config, key, value)

        return config

    def _evaluate_params(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        params: Dict[str, Any],
        symbol: str
    ) -> Optional[Dict[str, float]]:
        """
        Evaluate a single parameter combination.

        Returns metrics dictionary or None if insufficient trades.
        """
        try:
            config = self._create_strategy_config(strategy_class, params)
            strategy = strategy_class(config)

            # Check minimum data requirements
            if len(data) < strategy.min_periods:
                return None

            result = self._backtest_engine.run(strategy, data, symbol)

            # Check minimum trades
            if result.total_trades < self.optimization_config.min_trades_per_fold:
                return None

            return self._extract_metrics(result)

        except Exception:
            return None

    def _optimize_with_cv(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        params: Dict[str, Any],
        symbol: str,
        metric: MetricType
    ) -> Tuple[Optional[Dict[str, float]], List[Dict[str, Any]]]:
        """
        Evaluate parameters using cross-validation.

        Returns combined metrics and per-fold results.
        """
        n = len(data)
        window_size = self.optimization_config.cv_window_size or n // (
            self.optimization_config.cv_folds + 1
        )

        fold_results: List[Dict[str, Any]] = []
        fold_metrics: List[float] = []

        for fold in range(self.optimization_config.cv_folds):
            # Sliding window for CV
            start_idx = fold * window_size
            end_idx = start_idx + window_size * 2  # Train on window, test on next

            if end_idx > n:
                end_idx = n

            train_data = data.iloc[start_idx:start_idx + window_size]
            test_data = data.iloc[start_idx + window_size:end_idx]

            # Skip if insufficient data for this fold
            if len(train_data) < window_size * 0.5 or len(test_data) < 20:
                continue

            # Train: find best params on training data
            train_metrics = self._evaluate_params(
                strategy_class, train_data, params, symbol
            )

            if train_metrics is None:
                continue

            # Test: evaluate on held-out data
            test_metrics = self._evaluate_params(
                strategy_class, test_data, params, symbol
            )

            if test_metrics is not None:
                fold_results.append({
                    "fold": fold,
                    "train_score": train_metrics[metric.value],
                    "test_score": test_metrics[metric.value],
                    "cv_score": test_metrics[metric.value],
                    **{f"train_{k}": v for k, v in train_metrics.items()},
                    **{f"test_{k}": v for k, v in test_metrics.items()}
                })
                fold_metrics.append(test_metrics[metric.value])

        if not fold_metrics:
            return None, []

        # Average metrics across folds
        combined_metrics = {
            "sharpe_ratio": np.mean([r.get("sharpe_ratio", np.nan) for r in fold_results]),
            "sortino_ratio": np.mean([r.get("sortino_ratio", np.nan) for r in fold_results]),
            "total_return": np.mean([r.get("total_return", np.nan) for r in fold_results]),
            "win_rate": np.mean([r.get("win_rate", np.nan) for r in fold_results]),
            "profit_factor": np.mean([r.get("profit_factor", np.nan) for r in fold_results]),
            "calmar_ratio": np.mean([r.get("calmar_ratio", np.nan) for r in fold_results]),
            "max_drawdown": np.mean([r.get("max_drawdown", np.nan) for r in fold_results]),
            "max_drawdown_pct": np.mean([r.get("max_drawdown_pct", np.nan) for r in fold_results]),
        }

        return combined_metrics, fold_results

    def _extract_metrics(self, result: BacktestResult) -> Dict[str, float]:
        """Extract relevant metrics from backtest result."""
        return {
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "total_return": result.total_return,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "calmar_ratio": self._calculate_calmar(result),
            "max_drawdown": result.max_drawdown,
            "max_drawdown_pct": result.max_drawdown_pct,
        }

    def _calculate_calmar(self, result: BacktestResult) -> float:
        """Calculate Calmar ratio (annualized return / max drawdown)."""
        if result.max_drawdown_pct == 0:
            return 0.0

        # Annualized return assuming daily data
        n_days = (result.end_date - result.start_date).days if result.end_date and result.start_date else 252
        if n_days <= 0:
            n_days = 252

        annualized_return = result.total_return * (252 / n_days)
        return annualized_return / result.max_drawdown_pct

    def _find_best_params(
        self,
        all_results: pd.DataFrame,
        metric: MetricType
    ) -> Optional[Dict[str, Any]]:
        """Find best parameters from results DataFrame."""
        valid_results = all_results[all_results["valid"] == True]

        if len(valid_results) == 0:
            return None

        metric_col = metric.value

        # For drawdown metrics, we want to minimize
        if metric in (MetricType.MAX_DRAWDOWN, MetricType.NEGATIVE_DRAWDOWN):
            best_idx = valid_results[metric_col].idxmin()
        else:
            best_idx = valid_results[metric_col].idxmax()

        return valid_results.loc[best_idx].to_dict()

    def _log_progress(
        self,
        current: int,
        total: int,
        params: Dict[str, Any],
        metrics: Optional[Dict[str, float]],
        metric: MetricType
    ) -> None:
        """Log optimization progress."""
        if current % self.optimization_config.progress_interval == 0 or current == total:
            pct = (current / total) * 100
            metric_str = ""

            if metrics is not None and not np.isnan(metrics.get(metric.value, np.nan)):
                metric_str = f" | {metric.value}: {metrics[metric.value]:.4f}"

            # Truncate long param displays
            param_str = str(params)[:80] + "..." if len(str(params)) > 80 else str(params)

            print(f"[{current}/{total}] ({pct:.1f}%) Testing: {param_str}{metric_str}")


def grid_search(
    strategy_class: Type[BaseStrategy],
    data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    metric: MetricType = MetricType.SHARPE_RATIO,
    **kwargs
) -> OptimizationResult:
    """
    Convenience function for grid search optimization.

    Args:
        strategy_class: Strategy class to optimize
        data: Historical OHLCV data
        param_grid: Dictionary of parameter names to value lists
        metric: Metric to optimize
        **kwargs: Additional arguments passed to StrategyOptimizer

    Returns:
        OptimizationResult with best parameters

    Example:
        >>> result = grid_search(
        ...     RSIStrategy,
        ...     data,
        ...     {'rsi_period': [10, 14, 20]},
        ...     metric=MetricType.SHARPE_RATIO
        ... )
    """
    optimizer = StrategyOptimizer()
    opt_config = OptimizationConfig(metric=metric)
    optimizer.optimization_config = opt_config

    return optimizer.optimize(strategy_class, data, param_grid, metric=metric, **kwargs)
