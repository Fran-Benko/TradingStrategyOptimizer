"""
Statistical Arbitrage Strategy.

Implements mean reversion strategies on multiple securities using
statistical measures such as z-scores, Hurst exponent, and half-life
of mean reversion.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig


@dataclass
class StatisticalArbitrageConfig(StrategyConfig):
    """Configuration for statistical arbitrage strategy."""
    name: str = "StatisticalArbitrageStrategy"
    description: str = "Mean reversion statistical arbitrage strategy"
    
    # Lookback windows
    lookback_period: int = 30  # Period for calculating mean and std
    zscore_window: int = 20  # Window for z-score calculation
    correlation_window: int = 60  # Window for correlation calculation
    
    # Entry/exit thresholds
    entry_threshold: float = 2.0  # Z-score threshold for entry
    exit_threshold: float = 0.5  # Z-score threshold for exit
    max_position_threshold: float = 3.0  # Threshold for limiting position size
    
    # Portfolio parameters
    num_positions: int = 3  # Maximum number of simultaneous positions
    position_sizing: str = "equal"  # "equal", "inverse_vol", or "zscore_weighted"
    
    # Mean reversion parameters
    use_hurst_filter: bool = True  # Use Hurst exponent to filter signals
    min_hurst: float = 0.4  # Minimum Hurst exponent for mean reversion
    max_hurst: float = 0.6  # Maximum Hurst exponent for mean reversion
    use_half_life: bool = True  # Use half-life for position sizing
    max_half_life: int = 60  # Maximum half-life in periods
    
    # Ornstein-Uhlenbeck parameters
    ou_mean_window: int = 60  # Window for calculating OU mean
    ou_volatility_window: int = 30  # Window for calculating OU volatility
    ou_mean_reversion_speed: float = 0.1  # Fixed mean reversion speed (if not estimated)
    
    def validate(self) -> bool:
        """Validate statistical arbitrage parameters."""
        if not 10 <= self.lookback_period <= 500:
            raise ValueError("Lookback period must be between 10 and 500")
        if not 5 <= self.zscore_window <= 200:
            raise ValueError("Z-score window must be between 5 and 200")
        if not 0.1 <= self.entry_threshold <= 5.0:
            raise ValueError("Entry threshold must be between 0.1 and 5.0")
        if not 0.0 <= self.exit_threshold < self.entry_threshold:
            raise ValueError("Exit threshold must be non-negative and less than entry threshold")
        if self.position_sizing not in ("equal", "inverse_vol", "zscore_weighted"):
            raise ValueError("Position sizing must be 'equal', 'inverse_vol', or 'zscore_weighted'")
        if not 1 <= self.num_positions <= 20:
            raise ValueError("Number of positions must be between 1 and 20")
        if self.use_hurst_filter:
            if not 0.0 <= self.min_hurst <= self.max_hurst <= 1.0:
                raise ValueError("Invalid Hurst exponent bounds")
        return True


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    Statistical Arbitrage Strategy using Mean Reversion.
    
    This strategy identifies securities that have deviated from their
    historical mean and expects them to revert. It uses multiple techniques:
    
    1. Z-score calculation to identify deviations
    2. Hurst exponent to filter out trending (non-mean-reverting) securities
    3. Half-life estimation to determine position sizing
    4. Correlation matrix for portfolio construction
    
    Signals are generated based on z-score thresholds:
    - BUY when z-score < -entry_threshold (undervalued)
    - SELL when z-score > entry_threshold (overvalued)
    - CLOSE when |z-score| < exit_threshold
    
    Args:
        config: Statistical arbitrage configuration
        
    Example:
        >>> config = StatisticalArbitrageConfig(
        ...     lookback_period=30,
        ...     entry_threshold=2.0,
        ...     num_positions=3
        ... )
        >>> strategy = StatisticalArbitrageStrategy(config)
        >>> signals = strategy.generate_signals(data)
    """

    def __init__(self, config: Optional[StatisticalArbitrageConfig] = None):
        if config is None:
            config = StatisticalArbitrageConfig()
        config.validate()
        super().__init__(config)
        
        # Trading parameters
        self.lookback_period = config.lookback_period
        self.zscore_window = config.zscore_window
        self.correlation_window = config.correlation_window
        self.entry_threshold = config.entry_threshold
        self.exit_threshold = config.exit_threshold
        self.max_position_threshold = config.max_position_threshold
        self.num_positions = config.num_positions
        self.position_sizing = config.position_sizing
        
        # Mean reversion parameters
        self.use_hurst_filter = config.use_hurst_filter
        self.min_hurst = config.min_hurst
        self.max_hurst = config.max_hurst
        self.use_half_life = config.use_half_life
        self.max_half_life = config.max_half_life
        
        # OU parameters
        self.ou_mean_window = config.ou_mean_window
        self.ou_volatility_window = config.ou_volatility_window
        self.ou_mean_reversion_speed = config.ou_mean_reversion_speed
        
        # Internal state
        self._positions: Dict[str, int] = {}
        self._half_lives: Dict[str, float] = {}
        self._hurst_exponents: Dict[str, float] = {}

    @property
    def required_columns(self) -> List[str]:
        """Columns required in input DataFrame."""
        return ["close"]

    @property
    def min_periods(self) -> int:
        """Minimum periods required for the strategy."""
        return max(
            self.lookback_period,
            self.zscore_window,
            self.correlation_window,
            self.ou_mean_window
        )

    def _calculate_zscore(self, series: pd.Series) -> pd.Series:
        """
        Calculate rolling z-score of a series.
        
        Args:
            series: Price series
            
        Returns:
            Z-score series
        """
        rolling_mean = series.rolling(window=self.zscore_window).mean()
        rolling_std = series.rolling(window=self.zscore_window).std()
        
        # Avoid division by zero
        rolling_std = rolling_std.replace(0, np.nan).ffill().bfill()
        
        zscore = (series - rolling_mean) / rolling_std
        
        return zscore

    def _calculate_hurst_exponent(self, series: pd.Series) -> float:
        """
        Calculate Hurst exponent to determine if series is mean-reverting.
        
        H < 0.5: Mean-reverting
        H = 0.5: Random walk (Brownian motion)
        H > 0.5: Trending
        
        Args:
            series: Price series
            
        Returns:
            Hurst exponent
        """
        if len(series) < 100:
            return 0.5  # Default to random walk if insufficient data
        
        # Use R/S analysis
        try:
            lags = range(2, min(100, len(series) // 2))
            tau = []
            rs_values = []
            
            for lag in lags:
                # Calculate R/S statistic
                n_subseries = len(series) // lag
                if n_subseries < 2:
                    continue
                    
                rs_list = []
                for i in range(n_subseries):
                    subseries = series.iloc[i * lag:(i + 1) * lag]
                    mean = subseries.mean()
                    deviations = subseries - mean
                    cumsum = deviations.cumsum()
                    R = cumsum.max() - cumsum.min()
                    S = subseries.std()
                    
                    if S > 0:
                        rs_list.append(R / S)
                
                if rs_list:
                    tau.append(lag)
                    rs_values.append(np.mean(rs_list))
            
            if len(tau) < 5:
                return 0.5
            
            # Log-log regression: log(R/S) = H * log(n) + c
            log_n = np.log(tau)
            log_rs = np.log(rs_values)
            
            slope, _, _, _, _ = stats.linregress(log_n, log_rs)
            
            return max(0.0, min(1.0, slope))
            
        except Exception:
            return 0.5

    def _calculate_half_life(self, series: pd.Series) -> float:
        """
        Calculate mean reversion half-life using Ornstein-Uhlenbeck process.
        
        Half-life is the expected time for the spread/deviation to
        revert halfway to the mean.
        
        Args:
            series: Price or deviation series
            
        Returns:
            Half-life in periods
        """
        try:
            # Calculate returns
            returns = series.pct_change().dropna()
            
            if len(returns) < 10:
                return self.max_half_life
            
            # Lagged values
            y = returns.values
            X = np.column_stack([np.ones(len(returns) - 1), returns.shift(1).values[1:]])
            
            # OLS regression
            beta = np.linalg.lstsq(X, y[1:], rcond=None)[0]
            
            # Mean reversion speed (lambda)
            lambda_param = -beta[1]
            
            if lambda_param <= 0:
                return self.max_half_life
            
            # Half-life = ln(2) / lambda
            half_life = np.log(2) / lambda_param
            
            return min(max(1, half_life), self.max_half_life)
            
        except Exception:
            return self.max_half_life

    def _estimate_ou_parameters(self, series: pd.Series) -> Dict[str, float]:
        """
        Estimate Ornstein-Uhlenbeck process parameters.
        
        OU process: dX = theta * (mu - X) * dt + sigma * dW
        
        Args:
            series: Price or deviation series
            
        Returns:
            Dictionary with OU parameters
        """
        try:
            returns = series.pct_change().dropna()
            
            if len(returns) < self.ou_mean_window:
                return {
                    "theta": self.ou_mean_reversion_speed,
                    "mu": series.mean(),
                    "sigma": series.std(),
                    "half_life": self.max_half_life
                }
            
            # Calculate mean reversion speed using MLE
            X = series.values
            delta_t = 1
            
            # Discretized OU: X_{t+1} - X_t = theta * (mu - X_t) * delta_t + sigma * epsilon
            y = X[1:] - X[:-1]
            X_lagged = X[:-1]
            
            n = len(y)
            X_with_intercept = np.column_stack([np.ones(n), X_lagged])
            
            # OLS
            beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
            
            theta = -beta[1]  # Mean reversion speed
            mu = beta[0] / theta if theta > 0 else X.mean()
            
            # Calculate sigma from residuals
            residuals = y - (beta[0] + beta[1] * X_lagged)
            sigma = np.std(residuals)
            
            if sigma == 0:
                sigma = 1e-6
            
            # Calculate half-life
            if theta > 0:
                half_life = np.log(2) / theta
            else:
                half_life = self.max_half_life
            
            return {
                "theta": max(0.001, theta),
                "mu": mu,
                "sigma": sigma,
                "half_life": min(max(1, half_life), self.max_half_life)
            }
            
        except Exception:
            return {
                "theta": self.ou_mean_reversion_speed,
                "mu": series.mean(),
                "sigma": series.std(),
                "half_life": self.max_half_life
            }

    def _calculate_position_sizes(
        self, 
        zscores: Dict[str, float],
        prices: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate position sizes based on strategy parameters.
        
        Args:
            zscores: Dictionary of symbol -> z-score
            prices: Price data
            
        Returns:
            Dictionary of symbol -> position size
        """
        if not zscores:
            return {}
        
        if self.position_sizing == "equal":
            # Equal weight
            n = len(zscores)
            return {symbol: 1.0 / n for symbol in zscores}
        
        elif self.position_sizing == "inverse_vol":
            # Inverse volatility weighting
            vols = {}
            for symbol in zscores:
                if symbol in prices.columns:
                    returns = prices[symbol].pct_change().dropna()
                    vol = returns.std()
                    vols[symbol] = vol if vol > 0 else 1e-6
            
            inv_vols = {s: 1.0 / v for s, v in vols.items()}
            total = sum(inv_vols.values())
            return {s: iv / total for s, iv in inv_vols.items()}
        
        else:  # zscore_weighted
            # Weight by absolute z-score (stronger deviation = larger position)
            abs_zscores = {s: abs(z) for s, z in zscores.items()}
            total = sum(abs_zscores.values())
            if total > 0:
                return {s: az / total for s, az in abs_zscores.items()}
            return {s: 1.0 / len(zscores) for s in zscores}

    def _filter_signals(
        self,
        zscores: Dict[str, float],
        prices: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Filter trading signals based on Hurst exponent and half-life.
        
        Args:
            zscores: Dictionary of symbol -> z-score
            prices: Price data
            
        Returns:
            Filtered dictionary of symbol -> z-score
        """
        filtered = {}
        
        for symbol, zscore in zscores.items():
            if symbol not in prices.columns:
                continue
            
            series = prices[symbol]
            
            # Calculate Hurst exponent if filter is enabled
            if self.use_hurst_filter:
                if symbol not in self._hurst_exponents:
                    self._hurst_exponents[symbol] = self._calculate_hurst_exponent(series)
                
                hurst = self._hurst_exponents[symbol]
                
                # Only trade if mean-reverting (H < 0.5)
                if not (self.min_hurst <= hurst <= self.max_hurst):
                    continue
            
            # Calculate half-life if enabled
            if self.use_half_life:
                if symbol not in self._half_lives:
                    self._half_lives[symbol] = self._calculate_half_life(series)
                
                half_life = self._half_lives[symbol]
                
                # Skip if half-life is too long (not enough mean reversion)
                if half_life > self.max_half_life:
                    continue
            
            filtered[symbol] = zscore
        
        return filtered

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute statistical arbitrage signals for multiple securities.
        
        The data should contain multiple price columns (one per security).
        The strategy identifies mean-reverting opportunities across
        all securities and generates appropriate signals.
        
        Args:
            data: OHLCV data with multiple price columns
            
        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        # Handle single column case
        if "close" in data.columns and data.shape[1] == 1:
            return self._compute_single_symbol_signals(data)
        
        # Multi-symbol case
        return self._compute_multi_symbol_signals(data)

    def _compute_single_symbol_signals(self, data: pd.DataFrame) -> np.ndarray:
        """Compute signals for a single security."""
        close = data["close"]
        zscore = self._calculate_zscore(close)
        
        self._indicators["zscore"] = zscore
        self._indicators["mean"] = close.rolling(window=self.zscore_window).mean()
        self._indicators["std"] = close.rolling(window=self.zscore_window).std()
        
        # Calculate OU parameters
        if self.use_half_life or self.use_hurst_filter:
            ou_params = self._estimate_ou_parameters(close)
            self._indicators["half_life"] = pd.Series(
                ou_params["half_life"], index=close.index
            )
        
        signals = np.zeros(len(data))
        position = 0
        
        for i in range(len(data)):
            z = zscore.iloc[i]
            
            if np.isnan(z):
                signals[i] = 0
                continue
            
            # Check if at max position threshold (reduce exposure)
            if abs(z) > self.max_position_threshold:
                # Close any existing position
                if position != 0:
                    signals[i] = -position
                    position = 0
                continue
            
            if position == 0:
                # No position - check for entry
                if z < -self.entry_threshold:
                    signals[i] = 1
                    position = 1
                elif z > self.entry_threshold:
                    signals[i] = -1
                    position = -1
                else:
                    signals[i] = 0
            else:
                # In position - check for exit
                if position == 1 and z >= -self.exit_threshold:
                    signals[i] = -1
                    position = 0
                elif position == -1 and z <= self.exit_threshold:
                    signals[i] = 1
                    position = 0
                else:
                    signals[i] = 0
        
        return signals

    def _compute_multi_symbol_signals(self, data: pd.DataFrame) -> np.ndarray:
        """Compute signals for multiple securities."""
        symbols = [col for col in data.columns if col not in ["open", "high", "low", "close", "volume"]]
        if "close" not in symbols:
            symbols = data.select_dtypes(include=[np.number]).columns.tolist()
        
        signals = np.zeros((len(data), len(symbols)))
        
        # Calculate z-scores for all symbols
        zscores = pd.DataFrame(index=data.index)
        for symbol in symbols:
            zscores[symbol] = self._calculate_zscore(data[symbol])
        
        # Calculate rolling correlations
        if len(symbols) > 1 and len(data) > self.correlation_window:
            correlation_matrix = data[symbols].rolling(window=self.correlation_window).corr()
            self._indicators["correlation_matrix"] = correlation_matrix
        
        # Filter signals based on Hurst and half-life
        filtered_zscores = {}
        for symbol in symbols:
            if len(data) > self.lookback_period:
                series = data[symbol].iloc[-self.lookback_period:]
                if self.use_hurst_filter:
                    self._hurst_exponents[symbol] = self._calculate_hurst_exponent(series)
                if self.use_half_life:
                    self._half_lives[symbol] = self._calculate_half_life(series)
                filtered_zscores[symbol] = zscores[symbol].iloc[-1]
            else:
                filtered_zscores[symbol] = 0.0
        
        filtered_zscores = self._filter_signals(filtered_zscores, data)
        
        # Store indicators
        self._indicators["zscores"] = zscores
        self._indicators["hurst_exponents"] = pd.Series(self._hurst_exponents)
        self._indicators["half_lives"] = pd.Series(self._half_lives)
        
        # Generate signals for each symbol
        for idx, symbol in enumerate(symbols):
            position = 0
            symbol_zscore = zscores[symbol]
            
            for i in range(len(data)):
                z = symbol_zscore.iloc[i]
                
                if np.isnan(z):
                    signals[i, idx] = 0
                    continue
                
                # Check position limits
                if abs(z) > self.max_position_threshold:
                    if position != 0:
                        signals[i, idx] = -position
                        position = 0
                    continue
                
                if position == 0:
                    if symbol not in filtered_zscores:
                        continue
                        
                    if z < -self.entry_threshold:
                        signals[i, idx] = 1
                        position = 1
                    elif z > self.entry_threshold:
                        signals[i, idx] = -1
                        position = -1
                else:
                    if position == 1 and z >= -self.exit_threshold:
                        signals[i, idx] = -1
                        position = 0
                    elif position == -1 and z <= self.exit_threshold:
                        signals[i, idx] = 1
                        position = 0
        
        # Sum signals across symbols for combined signal
        combined_signals = signals.sum(axis=1)
        
        # Normalize to -1, 0, 1
        combined_signals = np.clip(combined_signals, -1, 1)
        
        return combined_signals

    def get_analysis_results(self) -> Dict[str, Any]:
        """
        Get comprehensive analysis results.
        
        Returns:
            Dictionary with analysis metrics
        """
        results = {
            "hurst_exponents": self._hurst_exponents.copy(),
            "half_lives": self._half_lives.copy(),
            "current_positions": self._positions.copy(),
        }
        
        zscores = self._indicators.get("zscores")
        if zscores is not None:
            results["current_zscores"] = {
                col: float(zscores[col].iloc[-1]) 
                for col in zscores.columns 
                if not np.isnan(zscores[col].iloc[-1])
            }
        
        return results

    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        params = super().get_parameters()
        params.update({
            "lookback_period": self.lookback_period,
            "zscore_window": self.zscore_window,
            "entry_threshold": self.entry_threshold,
            "exit_threshold": self.exit_threshold,
            "num_positions": self.num_positions,
            "position_sizing": self.position_sizing,
            "use_hurst_filter": self.use_hurst_filter,
            "use_half_life": self.use_half_life,
        })
        return params


class TripleScreenStatArbStrategy(StatisticalArbitrageStrategy):
    """
    Triple Screen Statistical Arbitrage Strategy.
    
    Combines three timeframes for robust signal generation:
    1. Weekly: Determine overall market direction (filter)
    2. Daily: Calculate z-score deviations
    3. Intraday: Entry timing with momentum confirmation
    
    This reduces false signals and improves entry timing.
    """

    def __init__(
        self,
        weekly_period: int = 5,
        daily_period: int = 20,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.5,
        momentum_confirmation: bool = True
    ):
        config = StatisticalArbitrageConfig(
            name="TripleScreenStatArbStrategy",
            description="Triple screen statistical arbitrage",
            lookback_period=daily_period,
            entry_threshold=entry_threshold,
            exit_threshold=exit_threshold
        )
        super().__init__(config)
        
        self.weekly_period = weekly_period
        self.momentum_confirmation = momentum_confirmation

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """Compute triple screen statistical arbitrage signals."""
        close = data["close"]
        
        # Timeframe 1: Weekly trend (using moving average)
        weekly_ma = close.rolling(window=self.weekly_period).mean()
        weekly_trend = close > weekly_ma
        
        # Timeframe 2: Daily z-score
        daily_zscore = self._calculate_zscore(close)
        
        # Timeframe 3: Intraday momentum (if enabled)
        if self.momentum_confirmation:
            returns = close.pct_change()
            momentum = returns.rolling(window=5).sum()
        else:
            momentum = pd.Series(1, index=close.index)
        
        # Store indicators
        self._indicators["weekly_ma"] = weekly_ma
        self._indicators["weekly_trend"] = weekly_trend
        self._indicators["momentum"] = momentum
        
        signals = np.zeros(len(data))
        position = 0
        
        for i in range(len(data)):
            weekly = weekly_trend.iloc[i]
            daily_z = daily_zscore.iloc[i]
            mom = momentum.iloc[i]
            
            if np.isnan(daily_z) or np.isnan(mom):
                signals[i] = 0
                continue
            
            if position == 0:
                # Check weekly trend for direction
                if weekly and daily_z < -self.entry_threshold:
                    # Uptrend + oversold = buy signal
                    if self.momentum_confirmation and mom < 0:
                        continue  # Wait for momentum to stabilize
                    signals[i] = 1
                    position = 1
                elif not weekly and daily_z > self.entry_threshold:
                    # Downtrend + overbought = sell signal
                    if self.momentum_confirmation and mom > 0:
                        continue
                    signals[i] = -1
                    position = -1
            else:
                if position == 1 and daily_z >= -self.exit_threshold:
                    signals[i] = -1
                    position = 0
                elif position == -1 and daily_z <= self.exit_threshold:
                    signals[i] = 1
                    position = 0
        
        return signals
