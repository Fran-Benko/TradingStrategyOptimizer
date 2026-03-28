"""
Walk-forward analysis module.

Provides walk-forward optimization and analysis to validate strategy
robustness across different market regimes. Supports both rolling and
expanding window approaches.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type

import numpy as np
import pandas as pd

from trading_system.backtesting.engine import BacktestConfig, BacktestEngine, BacktestResult
from trading_system.optimization.optimizer import MetricType, OptimizationConfig, StrategyOptimizer
from trading_system.strategies.base.base import BaseStrategy, StrategyConfig


class WindowType(Enum):
    """Walk-forward window types."""
    ROLLING = "rolling"  # Fixed window size, moves forward
    EXPANDING = "expanding"  # Grows over time, always starts from beginning


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward analysis."""
    window_type: WindowType = WindowType.ROLLING
    train_window: int = 252  # Training period in days
    test_window: int = 63  # Testing period in days (quarter)
    step_size: Optional[int] = None  # Forward step (default: test_window)
    min_train_periods: int = 126  # Minimum training periods
    min_test_periods: int = 20  # Minimum test periods
    min_trades_per_period: int = 5  # Minimum trades per period
    optimization_metric: MetricType = MetricType.SHARPE_RATIO
    optimization_config: Optional[OptimizationConfig] = None
    verbose: bool = True  # Progress logging

    def validate(self) -> bool:
        """Validate walk-forward configuration."""
        if self.train_window <= 0:
            raise ValueError("train_window must be positive")
        if self.test_window <= 0:
            raise ValueError("test_window must be positive")
        if self.min_train_periods <= 0:
            raise ValueError("min_train_periods must be positive")
        if self.min_test_periods <= 0:
            raise ValueError("min_test_periods must be positive")
        return True


@dataclass
class PeriodResult:
    """Results from a single walk-forward period."""
    period_index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    best_params: Dict[str, Any]
    in_sample_score: float
    out_of_sample_score: float
    in_sample_return: float
    out_of_sample_return: float
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    in_sample_max_dd: float
    out_of_sample_max_dd: float
    trade_count: int
    degradation_ratio: float  # Out-of-sample / In-sample ratio
    valid: bool = True
    reason: str = ""


@dataclass
class WalkForwardResult:
    """
    Results from walk-forward analysis.

    Contains detailed results for each period plus aggregated
    robustness metrics.

    Attributes:
        window_type: Type of window used (rolling or expanding)
        total_periods: Number of walk-forward periods analyzed
        in_sample_results: DataFrame with in-sample metrics
        out_of_sample_results: DataFrame with out-of-sample metrics
        period_results: List of per-period results
        stability_score: Measure of consistency across periods (0-1)
        walk_forward_return: Overall out-of-sample return
        degradation_ratio: Average in-sample vs out-of-sample ratio
        robustness_score: Composite robustness metric
        analysis_time: Time taken for full analysis
    """
    window_type: WindowType
    total_periods: int
    in_sample_results: pd.DataFrame
    out_of_sample_results: pd.DataFrame
    period_results: List[PeriodResult] = field(default_factory=list)
    stability_score: float = 0.0
    walk_forward_return: float = 0.0
    degradation_ratio: float = 0.0
    robustness_score: float = 0.0
    analysis_time: float = 0.0

    def summary(self) -> str:
        """Generate summary string of walk-forward results."""
        return f"""
=== Walk-Forward Analysis Results ===
Window Type: {self.window_type.value}
Total Periods: {self.total_periods}

Robustness Metrics:
  Stability Score: {self.stability_score:.4f}
  Walk-Forward Return: {self.walk_forward_return:.2%}
  Degradation Ratio: {self.degradation_ratio:.4f}
  Robustness Score: {self.robustness_score:.4f}

In-Sample Performance:
  Mean Return: {self.in_sample_results['return'].mean():.2%}
  Mean Sharpe: {self.in_sample_results['sharpe'].mean():.4f}

Out-of-Sample Performance:
  Mean Return: {self.out_of_sample_results['return'].mean():.2%}
  Mean Sharpe: {self.out_of_sample_results['sharpe'].mean():.4f}
"""

    def get_valid_periods(self) -> List[PeriodResult]:
        """Get only valid period results."""
        return [p for p in self.period_results if p.valid]

    def get_robust_params(self) -> Dict[str, Any]:
        """
        Get parameters that performed most consistently.

        Returns the parameter set from the period with the best
        out-of-sample performance.
        """
        valid = self.get_valid_periods()
        if not valid:
            return {}

        best = max(valid, key=lambda p: p.out_of_sample_score)
        return best.best_params

    def to_dataframe(self) -> pd.DataFrame:
        """Convert period results to DataFrame."""
        return pd.DataFrame([
            {
                "period": p.period_index,
                "train_start": p.train_start,
                "train_end": p.train_end,
                "test_start": p.test_start,
                "test_end": p.test_end,
                "best_params": str(p.best_params),
                "is_return": p.in_sample_return,
                "os_return": p.out_of_sample_return,
                "is_sharpe": p.in_sample_sharpe,
                "os_sharpe": p.out_of_sample_sharpe,
                "is_max_dd": p.in_sample_max_dd,
                "os_max_dd": p.out_of_sample_max_dd,
                "trade_count": p.trade_count,
                "degradation": p.degradation_ratio,
            }
            for p in self.period_results
        ])


class WalkForwardOptimizer:
    """
    Walk-forward optimizer for strategy parameters.

    Performs iterative optimization on rolling or expanding windows
    to validate strategy robustness across different market conditions.

    Args:
        backtest_config: Configuration for backtesting
        walk_forward_config: Configuration for walk-forward analysis

    Example:
        >>> config = WalkForwardConfig(
        ...     train_window=252,
        ...     test_window=63,
        ...     window_type=WindowType.ROLLING
        ... )
        >>> optimizer = WalkForwardOptimizer(walk_forward_config=config)
        >>> param_grid = {'rsi_period': [10, 14, 20]}
        >>> result = optimizer.optimize(RSIStrategy, data, param_grid)
        >>> print(result.robustness_score)
    """

    def __init__(
        self,
        backtest_config: Optional[BacktestConfig] = None,
        walk_forward_config: Optional[WalkForwardConfig] = None
    ):
        self.backtest_config = backtest_config or BacktestConfig()
        self.config = walk_forward_config or WalkForwardConfig()
        self.config.validate()

        self._backtest_engine = BacktestEngine(self.backtest_config)
        self._strategy_optimizer = StrategyOptimizer(
            backtest_config=backtest_config,
            optimization_config=self.config.optimization_config
        )

    def optimize(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        symbol: str = "WF_OPTIMIZE"
    ) -> WalkForwardResult:
        """
        Run walk-forward optimization.

        Args:
            strategy_class: Strategy class to optimize
            data: Historical OHLCV data
            param_grid: Dictionary of parameter names to value lists
            symbol: Symbol being traded

        Returns:
            WalkForwardResult with detailed period-by-period analysis

        Raises:
            ValueError: If data is insufficient for walk-forward analysis
        """
        if len(data) < self.config.min_train_periods + self.config.min_test_periods:
            raise ValueError(
                f"Insufficient data: need at least "
                f"{self.config.min_train_periods + self.config.min_test_periods} periods"
            )

        start_time = datetime.now()

        # Calculate window parameters
        step_size = self.config.step_size or self.config.test_window
        n_periods = self._calculate_n_periods(data)

        if n_periods == 0:
            raise ValueError("Insufficient data for any walk-forward periods")

        period_results: List[PeriodResult] = []

        for period_idx in range(n_periods):
            result = self._run_single_period(
                strategy_class, data, param_grid, symbol, period_idx
            )
            period_results.append(result)

            if self.config.verbose:
                self._log_period_progress(period_idx + 1, n_periods, result)

        # Calculate aggregated metrics
        analysis_time = (datetime.now() - start_time).total_seconds()
        aggregated = self._aggregate_results(period_results, n_periods)

        return WalkForwardResult(
            window_type=self.config.window_type,
            total_periods=n_periods,
            in_sample_results=self._create_in_sample_df(period_results),
            out_of_sample_results=self._create_out_of_sample_df(period_results),
            period_results=period_results,
            stability_score=aggregated["stability_score"],
            walk_forward_return=aggregated["walk_forward_return"],
            degradation_ratio=aggregated["degradation_ratio"],
            robustness_score=aggregated["robustness_score"],
            analysis_time=analysis_time
        )

    def _calculate_n_periods(self, data: pd.DataFrame) -> int:
        """Calculate number of walk-forward periods."""
        n = len(data)
        total_window = self.config.train_window + self.config.test_window
        step_size = self.config.step_size or self.config.test_window

        if self.config.window_type == WindowType.ROLLING:
            # Calculate how many complete periods fit
            return max(0, (n - self.config.train_window) // step_size)
        else:  # EXPANDING
            # Expanding uses same end point, different start
            return max(0, (n - total_window) // step_size) + 1

    def _run_single_period(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        symbol: str,
        period_idx: int
    ) -> PeriodResult:
        """Run single walk-forward period (train + test)."""
        step_size = self.config.step_size or self.config.test_window

        # Calculate indices
        if self.config.window_type == WindowType.ROLLING:
            train_end_idx = self.config.train_window + period_idx * step_size
        else:  # EXPANDING
            train_end_idx = self.config.train_window + period_idx * step_size

        test_end_idx = train_end_idx + self.config.test_window

        # Bounds check
        if test_end_idx > len(data):
            test_end_idx = len(data)

        if train_end_idx < self.config.min_train_periods:
            train_end_idx = self.config.min_train_periods

        # Extract data windows
        train_data = data.iloc[:train_end_idx]
        test_data = data.iloc[train_end_idx:test_end_idx]

        # Validate window sizes
        if len(train_data) < self.config.min_train_periods:
            return self._invalid_period(
                period_idx, train_data, test_data,
                "insufficient_training_data"
            )

        if len(test_data) < self.config.min_test_periods:
            return self._invalid_period(
                period_idx, train_data, test_data,
                "insufficient_test_data"
            )

        # Run optimization on training data
        train_result = self._strategy_optimizer.optimize(
            strategy_class, train_data, param_grid, symbol
        )

        best_params = train_result.best_params

        # If no valid optimization, return invalid
        if not best_params or np.isnan(train_result.best_score):
            return self._invalid_period(
                period_idx, train_data, test_data,
                "optimization_failed"
            )

        # Evaluate on in-sample (training) data
        in_sample_metrics = self._evaluate_params(
            strategy_class, train_data, best_params, symbol
        )

        # Evaluate on out-of-sample (test) data
        out_sample_metrics = self._evaluate_params(
            strategy_class, test_data, best_params, symbol
        )

        # Check minimum trades
        if out_sample_metrics is None or out_sample_metrics["trade_count"] < self.config.min_trades_per_period:
            return self._invalid_period(
                period_idx, train_data, test_data,
                "insufficient_trades"
            )

        # Calculate degradation ratio
        degradation = self._calculate_degradation(
            in_sample_metrics["score"],
            out_sample_metrics["score"]
        )

        return PeriodResult(
            period_index=period_idx,
            train_start=train_data.index[0],
            train_end=train_data.index[-1],
            test_start=test_data.index[0],
            test_end=test_data.index[-1],
            best_params=best_params,
            in_sample_score=in_sample_metrics["score"],
            out_of_sample_score=out_sample_metrics["score"],
            in_sample_return=in_sample_metrics["return"],
            out_of_sample_return=out_sample_metrics["return"],
            in_sample_sharpe=in_sample_metrics["sharpe"],
            out_of_sample_sharpe=out_sample_metrics["sharpe"],
            in_sample_max_dd=in_sample_metrics["max_dd"],
            out_of_sample_max_dd=out_sample_metrics["max_dd"],
            trade_count=out_sample_metrics["trade_count"],
            degradation_ratio=degradation,
            valid=True,
            reason=""
        )

    def _evaluate_params(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        params: Dict[str, Any],
        symbol: str
    ) -> Optional[Dict[str, float]]:
        """Evaluate parameters on data and return metrics."""
        try:
            config = self._create_strategy_config(strategy_class, params)
            strategy = strategy_class(config)

            if len(data) < strategy.min_periods:
                return None

            result = self._backtest_engine.run(strategy, data, symbol)

            # Get metric for optimization
            metric_col = self.config.optimization_metric.value
            score = getattr(result, metric_col, np.nan)

            return {
                "score": score,
                "return": result.total_return,
                "sharpe": result.sharpe_ratio,
                "sortino": result.sortino_ratio,
                "max_dd": result.max_drawdown_pct,
                "trade_count": result.total_trades,
                "win_rate": result.win_rate,
            }

        except Exception:
            return None

    def _create_strategy_config(
        self,
        strategy_class: Type[BaseStrategy],
        params: Dict[str, Any]
    ) -> StrategyConfig:
        """Create strategy config from parameters."""
        config = StrategyConfig(name=strategy_class.__name__)
        if hasattr(config, "__dict__"):
            for key, value in params.items():
                if not key.startswith("_"):
                    setattr(config, key, value)
        return config

    def _calculate_degradation(
        self,
        in_sample_score: float,
        out_sample_score: float
    ) -> float:
        """Calculate degradation ratio (OOS / IS)."""
        if in_sample_score == 0:
            return 0.0
        return out_sample_score / in_sample_score

    def _invalid_period(
        self,
        period_idx: int,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        reason: str
    ) -> PeriodResult:
        """Create an invalid period result."""
        return PeriodResult(
            period_index=period_idx,
            train_start=train_data.index[0] if len(train_data) > 0 else pd.Timestamp.min,
            train_end=train_data.index[-1] if len(train_data) > 0 else pd.Timestamp.min,
            test_start=test_data.index[0] if len(test_data) > 0 else pd.Timestamp.min,
            test_end=test_data.index[-1] if len(test_data) > 0 else pd.Timestamp.min,
            best_params={},
            in_sample_score=np.nan,
            out_of_sample_score=np.nan,
            in_sample_return=np.nan,
            out_of_sample_return=np.nan,
            in_sample_sharpe=np.nan,
            out_of_sample_sharpe=np.nan,
            in_sample_max_dd=np.nan,
            out_of_sample_max_dd=np.nan,
            trade_count=0,
            degradation_ratio=0.0,
            valid=False,
            reason=reason
        )

    def _aggregate_results(
        self,
        period_results: List[PeriodResult],
        total_periods: int
    ) -> Dict[str, float]:
        """Calculate aggregated walk-forward metrics."""
        valid_results = [p for p in period_results if p.valid]

        if not valid_results:
            return {
                "stability_score": 0.0,
                "walk_forward_return": 0.0,
                "degradation_ratio": 0.0,
                "robustness_score": 0.0
            }

        # Stability: coefficient of variation of OOS returns
        oos_returns = [p.out_of_sample_return for p in valid_results]
        mean_return = np.mean(oos_returns)
        std_return = np.std(oos_returns)

        if mean_return > 0:
            cv = std_return / abs(mean_return) if mean_return != 0 else 1.0
            stability_score = 1.0 / (1.0 + cv)  # Higher is better
        else:
            stability_score = 0.0

        # Walk-forward return: geometric mean of OOS returns
        valid_returns = [r + 1 for r in oos_returns if not np.isnan(r)]
        if valid_returns:
            walk_forward_return = np.prod(valid_returns) ** (1 / len(valid_returns)) - 1
        else:
            walk_forward_return = 0.0

        # Degradation ratio: average of period degradation
        degradation_ratios = [p.degradation_ratio for p in valid_results]
        degradation_ratio = np.mean(degradation_ratios)

        # Robustness score: composite of multiple factors
        # 0-1 scale combining stability, return, and degradation
        robustness_score = self._calculate_robustness_score(
            stability_score,
            walk_forward_return,
            degradation_ratio,
            valid_results
        )

        return {
            "stability_score": stability_score,
            "walk_forward_return": walk_forward_return,
            "degradation_ratio": degradation_ratio,
            "robustness_score": robustness_score
        }

    def _calculate_robustness_score(
        self,
        stability: float,
        wfr: float,
        degradation: float,
        valid_results: List[PeriodResult]
    ) -> float:
        """
        Calculate composite robustness score.

        Combines:
        - Stability (40%): How consistent is OOS performance
        - Walk-forward return (30%): Overall OOS profitability
        - Degradation (20%): IS vs OOS consistency
        - Win rate (10%): Percentage of periods with positive returns
        """
        # Normalize components to 0-1 scale
        stability_component = stability  # Already 0-1

        # WFR: clip to reasonable range
        wfr_clipped = max(-1.0, min(1.0, wfr))
        wfr_component = (wfr_clipped + 1.0) / 2.0  # Map -1..1 to 0..1

        # Degradation: higher is better (1.0 = perfect)
        degradation = max(0.0, min(1.0, degradation))

        # Win rate component
        positive_periods = sum(1 for p in valid_results if p.out_of_sample_return > 0)
        win_rate_component = positive_periods / len(valid_results) if valid_results else 0

        # Weighted combination
        robustness = (
            0.40 * stability_component +
            0.30 * wfr_component +
            0.20 * degradation +
            0.10 * win_rate_component
        )

        return robustness

    def _create_in_sample_df(
        self,
        period_results: List[PeriodResult]
    ) -> pd.DataFrame:
        """Create DataFrame of in-sample results."""
        valid = [p for p in period_results if p.valid]

        if not valid:
            return pd.DataFrame()

        return pd.DataFrame([
            {
                "period": p.period_index,
                "return": p.in_sample_return,
                "sharpe": p.in_sample_sharpe,
                "max_dd": p.in_sample_max_dd,
                "score": p.in_sample_score,
            }
            for p in valid
        ])

    def _create_out_of_sample_df(
        self,
        period_results: List[PeriodResult]
    ) -> pd.DataFrame:
        """Create DataFrame of out-of-sample results."""
        valid = [p for p in period_results if p.valid]

        if not valid:
            return pd.DataFrame()

        return pd.DataFrame([
            {
                "period": p.period_index,
                "return": p.out_of_sample_return,
                "sharpe": p.out_of_sample_sharpe,
                "max_dd": p.out_of_sample_max_dd,
                "score": p.out_of_sample_score,
                "trade_count": p.trade_count,
                "degradation": p.degradation_ratio,
            }
            for p in valid
        ])

    def _log_period_progress(
        self,
        current: int,
        total: int,
        result: PeriodResult
    ) -> None:
        """Log walk-forward period progress."""
        pct = (current / total) * 100
        status = "VALID" if result.valid else f"INVALID ({result.reason})"
        params_str = str(result.best_params)[:50] if result.best_params else "N/A"

        if result.valid:
            print(
                f"[{current}/{total}] ({pct:.1f}%) {status} | "
                f"OOS Sharpe: {result.out_of_sample_sharpe:.4f} | "
                f"Degradation: {result.degradation_ratio:.4f} | "
                f"Params: {params_str}"
            )
        else:
            print(f"[{current}/{total}] ({pct:.1f}%) {status}")


def walk_forward_analysis(
    strategy_class: Type[BaseStrategy],
    data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    train_window: int = 252,
    test_window: int = 63,
    window_type: WindowType = WindowType.ROLLING,
    **kwargs
) -> WalkForwardResult:
    """
    Convenience function for walk-forward analysis.

    Args:
        strategy_class: Strategy class to optimize
        data: Historical OHLCV data
        param_grid: Dictionary of parameter names to value lists
        train_window: Training period in bars
        test_window: Testing period in bars
        window_type: Rolling or expanding windows
        **kwargs: Additional arguments passed to WalkForwardOptimizer

    Returns:
        WalkForwardResult with robustness analysis

    Example:
        >>> result = walk_forward_analysis(
        ...     RSIStrategy,
        ...     data,
        ...     {'rsi_period': [10, 14, 20]},
        ...     train_window=252,
        ...     test_window=63
        ... )
        >>> print(f"Robustness: {result.robustness_score:.2f}")
    """
    config = WalkForwardConfig(
        train_window=train_window,
        test_window=test_window,
        window_type=window_type
    )
    optimizer = WalkForwardOptimizer(walk_forward_config=config)

    return optimizer.optimize(strategy_class, data, param_grid, **kwargs)
