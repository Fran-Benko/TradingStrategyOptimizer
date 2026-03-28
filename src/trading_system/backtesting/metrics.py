"""
Advanced metrics calculation for backtesting results.

Provides additional risk and performance metrics beyond the basic
metrics calculated in the engine.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass
class AdvancedMetrics:
    """Advanced performance and risk metrics."""
    calmar_ratio: float
    value_at_risk: float
    conditional_var: float
    tail_ratio: float
    skewness: float
    kurtosis: float
    omega_ratio: float
    information_ratio: float
    treynor_ratio: float
    r_squared: float
    ulcer_index: float
    recovery_time: Optional[float]
    max_consecutive_losses: int
    avg_consecutive_losses: float
    uptime_ratio: float
    gain_to_pain_ratio: float


def calculate_advanced_metrics(
    equity_curve: pd.Series,
    returns: pd.Series,
    trades: List,
    initial_capital: float,
    risk_free_rate: float = 0.0,
    benchmark_returns: Optional[pd.Series] = None
) -> AdvancedMetrics:
    """
    Calculate advanced risk and performance metrics.

    Args:
        equity_curve: Series of equity values over time
        returns: Series of period returns
        trades: List of Trade objects
        initial_capital: Starting capital
        risk_free_rate: Annual risk-free rate
        benchmark_returns: Benchmark returns for information ratio

    Returns:
        AdvancedMetrics with all calculated values
    """
    calmar = calculate_calmar_ratio(returns, equity_curve)
    var = calculate_value_at_risk(returns)
    cvar = calculate_conditional_var(returns)
    tail = calculate_tail_ratio(returns)
    skew = calculate_skewness(returns)
    kurt = calculate_kurtosis(returns)
    omega = calculate_omega_ratio(returns)
    
    info_ratio = 0.0
    treynor = 0.0
    r_squared = 0.0
    
    if benchmark_returns is not None and len(benchmark_returns) > 0:
        info_ratio = calculate_information_ratio(returns, benchmark_returns)
        treynor, r_squared = calculate_treynor_ratio(returns, benchmark_returns, risk_free_rate)
    
    ulcer = calculate_ulcer_index(equity_curve)
    recovery = calculate_recovery_time(equity_curve)
    max_consec = calculate_max_consecutive_losses(trades)
    avg_consec = calculate_avg_consecutive_losses(trades)
    uptime = calculate_uptime_ratio(equity_curve)
    gain_pain = calculate_gain_to_pain_ratio(returns)

    return AdvancedMetrics(
        calmar_ratio=calmar,
        value_at_risk=var,
        conditional_var=cvar,
        tail_ratio=tail,
        skewness=skew,
        kurtosis=kurt,
        omega_ratio=omega,
        information_ratio=info_ratio,
        treynor_ratio=treynor,
        r_squared=r_squared,
        ulcer_index=ulcer,
        recovery_time=recovery,
        max_consecutive_losses=max_consec,
        avg_consecutive_losses=avg_consec,
        uptime_ratio=uptime,
        gain_to_pain_ratio=gain_pain
    )


def calculate_calmar_ratio(returns: pd.Series, equity_curve: pd.Series) -> float:
    """Calculate Calmar ratio (CAGR / Max Drawdown)."""
    if len(returns) == 0:
        return 0.0

    years = len(returns) / 252
    if years == 0:
        return 0.0

    cagr = calculate_cagr(equity_curve)
    max_dd = calculate_max_drawdown(equity_curve)

    if max_dd == 0:
        return 0.0

    return cagr / max_dd


def calculate_cagr(equity_curve: pd.Series) -> float:
    """Calculate Compound Annual Growth Rate."""
    if len(equity_curve) < 2:
        return 0.0

    initial = equity_curve.iloc[0]
    final = equity_curve.iloc[-1]

    if initial <= 0:
        return 0.0

    years = len(equity_curve) / 252
    if years == 0:
        return 0.0

    return (final / initial) ** (1 / years) - 1


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Calculate maximum drawdown as a positive value."""
    if len(equity_curve) < 2:
        return 0.0

    cumulative = equity_curve / equity_curve.iloc[0]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max

    return abs(drawdown.min())


def calculate_value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Value at Risk (VaR).
    
    Args:
        returns: Series of returns
        confidence: Confidence level (default 95%)
    
    Returns:
        VaR as a positive loss value
    """
    if len(returns) == 0:
        return 0.0

    return -np.percentile(returns, (1 - confidence) * 100)


def calculate_conditional_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Conditional Value at Risk (CVaR / Expected Shortfall).
    
    Args:
        returns: Series of returns
        confidence: Confidence level (default 95%)
    
    Returns:
        CVaR as a positive loss value
    """
    if len(returns) == 0:
        return 0.0

    var = calculate_value_at_risk(returns, confidence)
    tail_returns = returns[returns <= -var]

    if len(tail_returns) == 0:
        return var

    return -tail_returns.mean()


def calculate_tail_ratio(returns: pd.Series) -> float:
    """Calculate tail ratio (95th percentile / 5th percentile)."""
    if len(returns) < 20:
        return 0.0

    percentile_95 = np.percentile(returns, 95)
    percentile_5 = np.percentile(returns, 5)

    if percentile_5 == 0:
        return 0.0

    return abs(percentile_95 / percentile_5)


def calculate_skewness(returns: pd.Series) -> float:
    """Calculate skewness of returns distribution."""
    if len(returns) < 3:
        return 0.0

    return returns.skew()


def calculate_kurtosis(returns: pd.Series) -> float:
    """Calculate kurtosis of returns distribution."""
    if len(returns) < 4:
        return 0.0

    return returns.kurtosis()


def calculate_omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    """
    Calculate Omega ratio.
    
    Ratio of weighted gains to weighted losses above threshold.
    """
    if len(returns) == 0:
        return 0.0

    gains = returns[returns > threshold] - threshold
    losses = threshold - returns[returns < threshold]

    if losses.sum() == 0:
        return float('inf') if gains.sum() > 0 else 0.0

    return gains.sum() / losses.sum()


def calculate_information_ratio(
    returns: pd.Series,
    benchmark_returns: pd.Series
) -> float:
    """Calculate Information Ratio (active return / tracking error)."""
    if len(returns) == 0 or len(benchmark_returns) == 0:
        return 0.0

    aligned_returns = returns.align(benchmark_returns, join='inner')
    if len(aligned_returns[0]) == 0:
        return 0.0

    active_returns = aligned_returns[0] - aligned_returns[1]
    tracking_error = active_returns.std()

    if tracking_error == 0:
        return 0.0

    return np.sqrt(252) * active_returns.mean() / tracking_error


def calculate_treynor_ratio(
    returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float
) -> tuple:
    """
    Calculate Treynor Ratio and R-squared.
    
    Returns:
        Tuple of (treynor_ratio, r_squared)
    """
    if len(returns) == 0 or len(benchmark_returns) == 0:
        return 0.0, 0.0

    aligned = returns.align(benchmark_returns, join='inner')
    if len(aligned[0]) < 2:
        return 0.0, 0.0

    excess_returns = aligned[0] - risk_free_rate / 252
    excess_benchmark = aligned[1] - risk_free_rate / 252

    covariance = excess_returns.cov(excess_benchmark)
    benchmark_variance = excess_benchmark.var()

    if benchmark_variance == 0:
        return 0.0, 0.0

    beta = covariance / benchmark_variance

    if beta == 0:
        return 0.0, 0.0

    treynor = np.sqrt(252) * excess_returns.mean() / beta

    correlation = excess_returns.corr(excess_benchmark)
    r_squared = correlation ** 2

    return treynor, r_squared


def calculate_ulcer_index(equity_curve: pd.Series) -> float:
    """
    Calculate Ulcer Index (measure of downside volatility).
    
    Based on depth and duration of drawdowns.
    """
    if len(equity_curve) < 2:
        return 0.0

    percentage = (equity_curve / equity_curve.expanding().max() - 1) * 100
    squared = percentage ** 2
    ulcer = np.sqrt(squared.mean())

    return ulcer


def calculate_recovery_time(equity_curve: pd.Series) -> Optional[float]:
    """
    Calculate average recovery time from drawdowns in years.
    
    Returns None if equity never recovers to previous highs.
    """
    if len(equity_curve) < 2:
        return None

    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max

    in_drawdown = drawdown < -0.01
    
    recovery_times = []
    drawdown_start = None
    
    for i, (is_dd, eq) in enumerate(zip(in_drawdown, equity_curve)):
        if is_dd and drawdown_start is None:
            drawdown_start = i
        elif not is_dd and drawdown_start is not None:
            recovery_times.append((i - drawdown_start) / 252)
            drawdown_start = None
    
    if not recovery_times:
        return None
    
    return np.mean(recovery_times)


def calculate_max_consecutive_losses(trades: List) -> int:
    """Calculate maximum consecutive losing trades."""
    if not trades:
        return 0

    max_consecutive = 0
    current_consecutive = 0

    for trade in trades:
        if trade.pnl < 0:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0

    return max_consecutive


def calculate_avg_consecutive_losses(trades: List) -> float:
    """Calculate average consecutive losing trades."""
    if not trades:
        return 0.0

    consecutive_losses = []
    current = 0

    for trade in trades:
        if trade.pnl < 0:
            current += 1
        else:
            if current > 0:
                consecutive_losses.append(current)
            current = 0

    if current > 0:
        consecutive_losses.append(current)

    return np.mean(consecutive_losses) if consecutive_losses else 0.0


def calculate_uptime_ratio(equity_curve: pd.Series) -> float:
    """
    Calculate uptime ratio (time above initial capital).
    
    Returns percentage of time the strategy was profitable.
    """
    if len(equity_curve) < 2:
        return 0.0

    initial = equity_curve.iloc[0]
    time_above = (equity_curve > initial).sum()

    return time_above / len(equity_curve)


def calculate_gain_to_pain_ratio(returns: pd.Series) -> float:
    """
    Calculate Gain to Pain ratio.
    
    Sum of returns / sum of absolute losses.
    """
    if len(returns) == 0:
        return 0.0

    total_return = returns.sum()
    pain = abs(returns[returns < 0]).sum()

    if pain == 0:
        return float('inf') if total_return > 0 else 0.0

    return total_return / pain


def calculate_rolling_sharpe(
    returns: pd.Series,
    window: int = 252,
    risk_free_rate: float = 0.0
) -> pd.Series:
    """Calculate rolling Sharpe ratio."""
    if len(returns) < window:
        return pd.Series()

    excess = returns - risk_free_rate / 252
    rolling_mean = excess.rolling(window).mean()
    rolling_std = returns.rolling(window).std()

    return np.sqrt(252) * rolling_mean / rolling_std


def calculate_rolling_drawdown(equity_curve: pd.Series) -> pd.Series:
    """Calculate rolling drawdown."""
    running_max = equity_curve.expanding().max()
    return (equity_curve - running_max) / running_max
