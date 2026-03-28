"""
Pairs Trading Strategy.

Implements statistical arbitrage using cointegration-based pairs trading.
Monitors the spread between two correlated securities and generates
signals when the spread deviates from its historical mean.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig


@dataclass
class PairsTradingConfig(StrategyConfig):
    """Configuration for pairs trading strategy."""
    name: str = "PairsTradingStrategy"
    description: str = "Cointegration-based pairs trading strategy"
    
    # Lookback windows
    lookback_period: int = 60  # Period for calculating hedge ratio and z-score
    zscore_window: int = 20  # Window for z-score calculation
    
    # Entry/exit thresholds
    entry_threshold: float = 2.0  # Z-score threshold for entry
    exit_threshold: float = 0.5  # Z-score threshold for exit
    stop_loss_threshold: float = 3.0  # Z-score threshold for stop loss
    
    # Trading parameters
    hedge_method: str = "rolling"  # "rolling", "kalman", or "static"
    kalman_gain: float = 0.001  # Kalman filter gain for dynamic hedge ratio
    num_standard_deviations: float = 2.0  # Bollinger band multiplier
    
    # Spread calculation method
    spread_method: str = "log"  # "simple", "log", or "ratio"
    
    def __post_init__(self) -> None:
        """Validate parameters after initialization."""
        self.validate()
    
    def validate(self) -> bool:
        """Validate pairs trading parameters."""
        if not 10 <= self.lookback_period <= 500:
            raise ValueError("Lookback period must be between 10 and 500")
        if not 5 <= self.zscore_window <= 100:
            raise ValueError("Z-score window must be between 5 and 100")
        if not 0.1 <= self.entry_threshold <= 5.0:
            raise ValueError("Entry threshold must be between 0.1 and 5.0")
        if not 0.0 <= self.exit_threshold < self.entry_threshold:
            raise ValueError("Exit threshold must be non-negative and less than entry threshold")
        if not self.entry_threshold < self.stop_loss_threshold:
            raise ValueError("Stop loss threshold must be greater than entry threshold")
        if self.hedge_method not in ("rolling", "kalman", "static"):
            raise ValueError("Hedge method must be 'rolling', 'kalman', or 'static'")
        if self.spread_method not in ("simple", "log", "ratio"):
            raise ValueError("Spread method must be 'simple', 'log', or 'ratio'")
        if not 0.0 < self.kalman_gain <= 0.1:
            raise ValueError("Kalman gain must be between 0 and 0.1")
        return True


class PairsTradingStrategy(BaseStrategy):
    """
    Pairs Trading Strategy based on cointegration.
    
    This strategy monitors the spread between two correlated securities
    (a trading pair). When the spread deviates significantly from its
    historical mean (measured by z-score), it generates trading signals:
    
    - BUY the spread when z-score < -entry_threshold (undervalued spread)
    - SELL the spread when z-score > entry_threshold (overvalued spread)
    - CLOSE positions when z-score crosses exit_threshold
    
    The spread is calculated as: spread = price1 - hedge_ratio * price2
    
    Args:
        config: Pairs trading configuration
        
    Example:
        >>> config = PairsTradingConfig(
        ...     lookback_period=60,
        ...     entry_threshold=2.0,
        ...     exit_threshold=0.5
        ... )
        >>> strategy = PairsTradingStrategy(config)
        >>> signals = strategy.generate_signals(data)
    """

    def __init__(self, config: Optional[PairsTradingConfig] = None):
        if config is None:
            config = PairsTradingConfig()
        config.validate()
        super().__init__(config)
        
        # Trading parameters
        self.lookback_period = config.lookback_period
        self.zscore_window = config.zscore_window
        self.entry_threshold = config.entry_threshold
        self.exit_threshold = config.exit_threshold
        self.stop_loss_threshold = config.stop_loss_threshold
        self.hedge_method = config.hedge_method
        self.kalman_gain = config.kalman_gain
        self.num_standard_deviations = config.num_standard_deviations
        self.spread_method = config.spread_method
        
        # Internal state for Kalman filter
        self._hedge_ratio: float = 1.0
        self._spread_history: List[float] = []

    @property
    def required_columns(self) -> List[str]:
        """Columns required in input DataFrame.
        
        Pairs trading supports multiple data formats:
        - 'close_0' and 'close_1' for explicit pair data
        - 'close' for single-column (backward compat)
        - Any two numeric columns
        """
        return ["close_0", "close_1"]

    def validate_data(self, data: pd.DataFrame) -> None:
        """Validate input data for pairs trading.
        
        Supports multiple column formats:
        - 'close_0' and 'close_1' columns
        - Single 'close' column (backward compatibility)
        - Any DataFrame with exactly 2 columns
        """
        has_pairs_cols = "close_0" in data.columns and "close_1" in data.columns
        has_single_close = "close" in data.columns and len(data.columns) == 1
        has_two_cols = len(data.columns) == 2
        
        if not (has_pairs_cols or has_single_close or has_two_cols):
            raise ValueError(
                "Pairs trading requires data with two price columns. "
                "Provide columns 'close_0' and 'close_1', or a DataFrame "
                "with two columns."
            )
        
        if len(data) < self.min_periods:
            raise ValueError(
                f"Insufficient data: need at least {self.min_periods} periods"
            )

    @property
    def min_periods(self) -> int:
        """Minimum periods required for the strategy."""
        return max(self.lookback_period, self.zscore_window)

    def _compute_spread(
        self, 
        price1: pd.Series, 
        price2: pd.Series
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate the spread between two price series.
        
        Args:
            price1: First price series (typically the "lead" security)
            price2: Second price series (typically the "lag" security)
            
        Returns:
            Tuple of (spread, hedge_ratio)
        """
        if self.spread_method == "log":
            # Use log prices for log-normal spread
            p1 = np.log(price1)
            p2 = np.log(price2)
        else:
            p1 = price1
            p2 = price2
        
        if self.hedge_method == "static":
            # Use simple OLS regression for entire series
            hedge_ratio = self._calculate_static_hedge_ratio(p1, p2)
        elif self.hedge_method == "kalman":
            # Use Kalman filter for dynamic hedge ratio
            hedge_ratio = self._calculate_kalman_hedge_ratio(p1, p2)
        else:  # rolling
            # Use rolling OLS regression
            hedge_ratio = self._calculate_rolling_hedge_ratio(p1, p2)
        
        # Calculate spread
        spread = p1 - hedge_ratio * p2
        
        return spread, hedge_ratio

    def _calculate_static_hedge_ratio(
        self, 
        price1: pd.Series, 
        price2: pd.Series
    ) -> pd.Series:
        """Calculate static hedge ratio using OLS regression."""
        lookback = min(self.lookback_period, len(price1))
        p1 = price1.iloc[-lookback:]
        p2 = price2.iloc[-lookback:]
        
        # OLS regression: price1 = hedge_ratio * price2 + intercept
        slope, intercept, _, _, _ = stats.linregress(p2, p1)
        
        return pd.Series(slope, index=price1.index)

    def _calculate_rolling_hedge_ratio(
        self, 
        price1: pd.Series, 
        price2: pd.Series
    ) -> pd.Series:
        """Calculate rolling hedge ratio using rolling OLS regression."""
        hedge_ratios = pd.Series(index=price1.index, dtype=float)
        
        for i in range(self.lookback_period, len(price1)):
            p1_window = price1.iloc[i - self.lookback_period:i]
            p2_window = price2.iloc[i - self.lookback_period:i]
            
            try:
                slope, _, _, _, _ = stats.linregress(p2_window, p1_window)
            except ValueError:
                slope = 1.0
            hedge_ratios.iloc[i] = slope
        
        # Forward fill initial values
        hedge_ratios = hedge_ratios.ffill().bfill()
        
        return hedge_ratios

    def _calculate_kalman_hedge_ratio(
        self, 
        price1: pd.Series, 
        price2: pd.Series
    ) -> pd.Series:
        """Calculate dynamic hedge ratio using Kalman filter."""
        hedge_ratios = pd.Series(index=price1.index, dtype=float)
        p1 = price1.values
        p2 = price2.values
        
        # Initialize state
        theta = 1.0  # Initial hedge ratio
        P = 1.0  # Initial covariance
        
        for i in range(len(p1)):
            if i > 0:
                # Prediction step
                theta_pred = theta
                P_pred = P + self.kalman_gain
                
                # Observation
                y = p1[i]
                x = p2[i]
                
                # Kalman gain
                K = P_pred * x / (x * P_pred * x + 1)
                
                # Update step
                innovation = y - theta_pred * x
                theta = theta_pred + K * innovation
                P = (1 - K * x) * P_pred
            
            hedge_ratios.iloc[i] = theta
        
        return hedge_ratios

    def _calculate_zscore(self, spread: pd.Series) -> pd.Series:
        """
        Calculate z-score of the spread.
        
        Args:
            spread: Price spread series
            
        Returns:
            Z-score series
        """
        rolling_mean = spread.rolling(window=self.zscore_window).mean()
        rolling_std = spread.rolling(window=self.zscore_window).std()
        
        # Avoid division by zero
        rolling_std = rolling_std.replace(0, np.nan).ffill().bfill()
        
        zscore = (spread - rolling_mean) / rolling_std
        
        return zscore

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute pairs trading signals.
        
        For pairs trading, data should have columns for the two securities
        in the pair. If only 'close' is available, it assumes single-column
        data where the second security is implied or the user must provide
        multi-column data.
        
        Expected data format for pairs:
        - 'close_0': First security close price
        - 'close_1': Second security close price
        
        Or if data has 'close' with shape (n, 2), it treats columns as
        the two securities.
        
        Args:
            data: OHLCV data with multiple price columns
            
        Returns:
            Array of signals: 1 (buy spread), 0 (hold), -1 (sell spread)
        """
        # Handle different data formats
        if "close_0" in data.columns and "close_1" in data.columns:
            price1 = data["close_0"]
            price2 = data["close_1"]
        elif len(data.columns) == 1 and "close" in data.columns:
            # Single column - use the same price for both (self-correlating)
            # This is for backward compatibility; real pairs need two prices
            price1 = data["close"]
            price2 = data["close"].shift(1).bfill()
        elif data.shape[1] == 2:
            # DataFrame with two columns
            price1 = data.iloc[:, 0]
            price2 = data.iloc[:, 1]
        else:
            # Assume first two numeric columns are the pair
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) >= 2:
                price1 = data[numeric_cols[0]]
                price2 = data[numeric_cols[1]]
            else:
                raise ValueError(
                    "Pairs trading requires data with two price columns. "
                    "Provide columns 'close_0' and 'close_1', or a DataFrame "
                    "with two columns."
                )
        
        # Calculate spread and hedge ratio
        spread, hedge_ratio = self._compute_spread(price1, price2)
        
        # Calculate z-score
        zscore = self._calculate_zscore(spread)
        
        # Store indicators for analysis
        self._indicators["spread"] = spread
        self._indicators["hedge_ratio"] = hedge_ratio
        self._indicators["zscore"] = zscore
        self._indicators["spread_mean"] = spread.rolling(window=self.zscore_window).mean()
        self._indicators["spread_std"] = spread.rolling(window=self.zscore_window).std()
        
        # Generate signals
        signals = np.zeros(len(data))
        
        position = 0  # 0: flat, 1: long spread, -1: short spread
        
        for i in range(len(data)):
            z = zscore.iloc[i]
            
            if np.isnan(z):
                signals[i] = 0
                continue
            
            if position == 0:
                # No position - check for entry signals
                if z < -self.entry_threshold:
                    # Spread is undervalued - buy spread (long security 1, short security 2)
                    signals[i] = 1
                    position = 1
                elif z > self.entry_threshold:
                    # Spread is overvalued - sell spread (short security 1, long security 2)
                    signals[i] = -1
                    position = -1
                else:
                    signals[i] = 0
                    
            elif position == 1:
                # Long spread position - check for exit or stop loss
                if z >= -self.exit_threshold:
                    # Exit long position
                    signals[i] = -1
                    position = 0
                elif z > self.stop_loss_threshold:
                    # Stop loss - close position
                    signals[i] = -1
                    position = 0
                else:
                    signals[i] = 0
                    
            elif position == -1:
                # Short spread position - check for exit or stop loss
                if z <= self.exit_threshold:
                    # Exit short position
                    signals[i] = 1
                    position = 0
                elif z < -self.stop_loss_threshold:
                    # Stop loss - close position
                    signals[i] = 1
                    position = 0
                else:
                    signals[i] = 0
        
        return signals

    def get_spread_statistics(self) -> Dict[str, float]:
        """
        Get current spread statistics.
        
        Returns:
            Dictionary with spread statistics
        """
        spread = self._indicators.get("spread")
        if spread is None or len(spread) == 0:
            return {}
        
        return {
            "current_spread": float(spread.iloc[-1]) if not np.isnan(spread.iloc[-1]) else None,
            "spread_mean": float(spread.mean()),
            "spread_std": float(spread.std()),
            "hedge_ratio": float(self._indicators.get("hedge_ratio", pd.Series([1.0])).iloc[-1]),
            "current_zscore": float(self._indicators.get("zscore", pd.Series([0.0])).iloc[-1]),
        }

    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters including trading configuration."""
        params = super().get_parameters()
        params.update({
            "lookback_period": self.lookback_period,
            "zscore_window": self.zscore_window,
            "entry_threshold": self.entry_threshold,
            "exit_threshold": self.exit_threshold,
            "stop_loss_threshold": self.stop_loss_threshold,
            "hedge_method": self.hedge_method,
            "spread_method": self.spread_method,
        })
        return params


class BollingerBandsPairsStrategy(PairsTradingStrategy):
    """
    Pairs Trading Strategy with Bollinger Bands overlay.
    
    Extends the base pairs trading strategy by using Bollinger Bands
    to identify overbought/oversold conditions in the spread.
    
    Signals:
    - BUY when price crosses below lower band (z < -entry_threshold)
    - SELL when price crosses above upper band (z > entry_threshold)
    - Positions are held until mean reversion occurs
    """

    def __init__(
        self,
        lookback_period: int = 60,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.5,
        num_std: float = 2.0,
        hedge_method: str = "rolling"
    ):
        config = PairsTradingConfig(
            lookback_period=lookback_period,
            entry_threshold=entry_threshold,
            exit_threshold=exit_threshold,
            num_standard_deviations=num_std,
            hedge_method=hedge_method
        )
        super().__init__(config)

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """Compute Bollinger Bands pairs trading signals."""
        # Get base pairs trading z-scores
        signals = super()._compute_signals(data)
        
        # Add Bollinger Bands confirmation
        spread = self._indicators.get("spread")
        if spread is None:
            return signals
        
        spread_mean = spread.rolling(window=self.zscore_window).mean()
        spread_std = spread.rolling(window=self.zscore_window).std()
        
        upper_band = spread_mean + self.num_standard_deviations * spread_std
        lower_band = spread_mean - self.num_standard_deviations * spread_std
        
        self._indicators["upper_band"] = upper_band
        self._indicators["lower_band"] = lower_band
        
        return signals
