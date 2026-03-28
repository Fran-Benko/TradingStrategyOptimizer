"""
Momentum ML Strategy.

Implements a simple momentum prediction strategy using price features.
Uses features like returns, volatility, and RSI for momentum signals.
Can optionally use a simple ML model for prediction (sklearn if available).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from trading_system.strategies.base.base import BaseStrategy, StrategyConfig
from trading_system.strategies.indicators import (
    calculate_rsi,
    calculate_sma,
    calculate_ema,
    calculate_atr,
)


@dataclass
class MomentumMLConfig(StrategyConfig):
    """Configuration for Momentum ML strategy."""
    name: str = "MomentumMLStrategy"
    description: str = "ML-based momentum prediction strategy"
    feature_lookback: int = 20
    prediction_horizon: int = 5
    momentum_threshold: float = 0.01
    volatility_threshold: float = 0.02
    min_confidence: float = 0.6
    use_ml_model: bool = True
    rsi_period: int = 14
    atr_period: int = 14

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()

    def validate(self) -> bool:
        """Validate momentum ML parameters."""
        if not 5 <= self.feature_lookback <= 100:
            raise ValueError("Feature lookback must be between 5 and 100")
        if not 1 <= self.prediction_horizon <= 50:
            raise ValueError("Prediction horizon must be between 1 and 50")
        if not -1 <= self.momentum_threshold <= 1:
            raise ValueError("Momentum threshold must be between -1 and 1")
        if not 0 <= self.volatility_threshold <= 1:
            raise ValueError("Volatility threshold must be between 0 and 1")
        if not 0.1 <= self.min_confidence <= 1.0:
            raise ValueError("Min confidence must be between 0.1 and 1.0")
        if not 2 <= self.rsi_period <= 100:
            raise ValueError("RSI period must be between 2 and 100")
        if not 2 <= self.atr_period <= 100:
            raise ValueError("ATR period must be between 2 and 100")
        return True


class MomentumMLStrategy(BaseStrategy):
    """
    Momentum ML Strategy.

    Uses price-based features to predict momentum direction.
    Features include:
    - Returns (various timeframes)
    - Volatility measures
    - RSI
    - Moving average relationships

    When use_ml_model=True, fits a simple logistic regression to
    combine features. Falls back to rule-based scoring when
    sklearn is unavailable.

    Args:
        config: Strategy configuration

    Example:
        >>> config = MomentumMLConfig(
        ...     feature_lookback=20,
        ...     prediction_horizon=5,
        ...     momentum_threshold=0.01
        ... )
        >>> strategy = MomentumMLStrategy(config)
        >>> signals = strategy.generate_signals(data)
        >>> confidence = strategy.get_confidence(data)
        >>> print(f"Signal confidence: {confidence:.2%}")
    """

    def __init__(self, config: Optional[MomentumMLConfig] = None):
        if config is None:
            config = MomentumMLConfig()
        config.validate()
        super().__init__(config)
        self.feature_lookback = config.feature_lookback
        self.prediction_horizon = config.prediction_horizon
        self.momentum_threshold = config.momentum_threshold
        self.volatility_threshold = config.volatility_threshold
        self.min_confidence = config.min_confidence
        self.use_ml_model = config.use_ml_model
        self.rsi_period = config.rsi_period
        self.atr_period = config.atr_period
        
        self._model = None
        self._feature_names = None
        self._model_trained = False

    @property
    def required_columns(self) -> List[str]:
        """Required columns in input DataFrame."""
        return ["close", "high", "low"]

    @property
    def min_periods(self) -> int:
        """Minimum periods required."""
        return max(
            self.feature_lookback + self.prediction_horizon,
            self.rsi_period + 5,
            self.atr_period + 5
        )

    def _create_features(
        self,
        data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Create feature matrix from OHLCV data.

        Args:
            data: OHLCV data

        Returns:
            Tuple of (features DataFrame, forward returns)
        """
        close = data["close"]
        high = data["high"]
        low = data["low"]
        
        features = pd.DataFrame(index=data.index)
        
        features["return_1d"] = close.pct_change(1)
        features["return_5d"] = close.pct_change(5)
        features["return_10d"] = close.pct_change(10)
        features["return_lookback"] = close.pct_change(self.feature_lookback)
        
        features["volatility_5d"] = close.pct_change().rolling(5).std()
        features["volatility_10d"] = close.pct_change().rolling(10).std()
        features["volatility_lookback"] = close.pct_change().rolling(
            self.feature_lookback
        ).std()
        
        features["rsi"] = calculate_rsi(close, period=self.rsi_period)
        
        features["atr"] = calculate_atr(high, low, close, period=self.atr_period)
        features["atr_percent"] = features["atr"] / close
        
        sma_fast = calculate_sma(close, period=10)
        sma_medium = calculate_sma(close, period=30)
        sma_slow = calculate_sma(close, period=50)
        
        features["sma_fast_slow_ratio"] = (sma_fast - sma_slow) / sma_slow
        features["sma_fast_medium_ratio"] = (sma_fast - sma_medium) / sma_medium
        features["sma_medium_slow_ratio"] = (sma_medium - sma_slow) / sma_slow
        
        ema_short = calculate_ema(close, period=12)
        ema_long = calculate_ema(close, period=26)
        features["ema_diff"] = (ema_short - ema_long) / ema_long
        
        features["high_low_range"] = (high - low) / close
        features["close_position"] = (close - low) / (high - low + 1e-10)
        
        features["momentum"] = close - close.shift(self.prediction_horizon)
        features["momentum_pct"] = close.pct_change(self.prediction_horizon)
        
        forward_returns = close.pct_change(self.prediction_horizon).shift(
            -self.prediction_horizon
        )
        
        features = features.fillna(0)
        features = features.replace([np.inf, -np.inf], 0)
        
        return features, forward_returns

    def _train_model(
        self,
        features: pd.DataFrame,
        labels: pd.Series
    ) -> None:
        """
        Train the ML model on historical data.

        Args:
            features: Feature matrix
            labels: Forward returns (binary: up/down)
        """
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline
            
            valid_mask = labels.notna() & features.notna().all(axis=1)
            X = features[valid_mask].values
            y = (labels[valid_mask] > 0).astype(int).values
            
            if len(np.unique(y)) < 2:
                self._model = None
                return
            
            self._model = Pipeline([
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(
                    C=1.0,
                    max_iter=1000,
                    random_state=42
                ))
            ])
            self._model.fit(X, y)
            self._feature_names = features.columns.tolist()
            self._model_trained = True
            
        except ImportError:
            self._model = None
            self._model_trained = False

    def _predict_rule_based(
        self,
        features: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Rule-based momentum prediction.

        Args:
            features: Feature matrix

        Returns:
            Tuple of (signals, confidence scores)
        """
        signals = np.zeros(len(features))
        confidences = np.zeros(len(features))
        
        weights = {
            "return_lookback": 0.25,
            "rsi": 0.15,
            "sma_fast_slow_ratio": 0.20,
            "momentum_pct": 0.25,
            "ema_diff": 0.15
        }
        
        for i in range(self.min_periods, len(features)):
            score = 0.0
            
            return_lookback = features["return_lookback"].iloc[i]
            if return_lookback > self.momentum_threshold:
                score += weights["return_lookback"]
            elif return_lookback < -self.momentum_threshold:
                score -= weights["return_lookback"]
            
            rsi = features["rsi"].iloc[i]
            if rsi > 60:
                score += weights["rsi"]
            elif rsi < 40:
                score -= weights["rsi"]
            
            sma_ratio = features["sma_fast_slow_ratio"].iloc[i]
            if sma_ratio > 0.02:
                score += weights["sma_fast_slow_ratio"]
            elif sma_ratio < -0.02:
                score -= weights["sma_fast_slow_ratio"]
            
            momentum = features["momentum_pct"].iloc[i]
            if momentum > self.momentum_threshold:
                score += weights["momentum_pct"]
            elif momentum < -self.momentum_threshold:
                score -= weights["momentum_pct"]
            
            ema_diff = features["ema_diff"].iloc[i]
            if ema_diff > 0.01:
                score += weights["ema_diff"]
            elif ema_diff < -0.01:
                score -= weights["ema_diff"]
            
            confidence = min(abs(score) / 0.5, 1.0)
            
            if score > 0.3 and confidence >= self.min_confidence:
                signals[i] = 1
            elif score < -0.3 and confidence >= self.min_confidence:
                signals[i] = -1
            
            confidences[i] = confidence
        
        return signals, confidences

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute momentum ML trading signals.

        Args:
            data: OHLCV data

        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        features, forward_returns = self._create_features(data)
        
        self._indicators["features"] = features
        
        if self.use_ml_model and self._model is None:
            self._train_model(features, forward_returns)
        
        if self.use_ml_model and self._model is not None:
            signals, confidences = self._predict_with_model(features)
        else:
            signals, confidences = self._predict_rule_based(features)
        
        self._indicators["confidence"] = pd.Series(confidences, index=data.index)
        
        signals = self._apply_position_logic(signals, confidences)
        
        return signals

    def _predict_with_model(
        self,
        features: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict using trained ML model.

        Args:
            features: Feature matrix

        Returns:
            Tuple of (signals, confidence scores)
        """
        try:
            X = features.values
            
            probabilities = self._model.predict_proba(X)
            predictions = self._model.predict(X)
            
            confidences = np.max(probabilities, axis=1)
            
            signals = np.where(
                (predictions == 1) & (confidences >= self.min_confidence), 1,
                np.where(
                    (predictions == 0) & (confidences >= self.min_confidence), -1,
                    0
                )
            )
            
            return signals, confidences
            
        except Exception:
            return self._predict_rule_based(features)

    def _apply_position_logic(
        self,
        signals: np.ndarray,
        confidences: np.ndarray
    ) -> np.ndarray:
        """
        Apply position management logic to signals.

        Args:
            signals: Raw signals
            confidences: Confidence scores

        Returns:
            Filtered signals
        """
        final_signals = signals.copy()
        
        in_position = False
        
        for i in range(len(final_signals)):
            if final_signals[i] == 1 and not in_position:
                in_position = True
            elif final_signals[i] == -1 and in_position:
                final_signals[i] = -1
                in_position = False
            elif in_position and confidences[i] < self.min_confidence * 0.5:
                final_signals[i] = -1
                in_position = False
            else:
                final_signals[i] = 0
        
        return final_signals

    def get_confidence(self, data: pd.DataFrame) -> float:
        """
        Get current signal confidence.

        Args:
            data: OHLCV data

        Returns:
            Current confidence score (0-1)
        """
        self.generate_signals(data)
        confidence = self._indicators.get("confidence")
        if confidence is not None and len(confidence) > 0:
            return float(confidence.iloc[-1])
        return 0.0

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """
        Get feature importance scores if model is trained.

        Returns:
            DataFrame with feature names and importance scores
        """
        if not self._model_trained or self._model is None:
            return None
        
        try:
            importances = self._model.named_steps["classifier"].coef_[0]
            return pd.DataFrame({
                "feature": self._feature_names,
                "importance": np.abs(importances)
            }).sort_values("importance", ascending=False)
        except Exception:
            return None


class SimpleMomentumStrategy(BaseStrategy):
    """
    Simple Momentum Strategy.

    A lightweight momentum strategy without ML components.
    Uses RSI, returns, and volatility for signal generation.

    Args:
        rsi_period: RSI period (default: 14)
        rsi_oversold: Oversold threshold (default: 30)
        rsi_overbought: Overbought threshold (default: 70)
        momentum_period: Momentum calculation period (default: 10)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        momentum_period: int = 10
    ):
        config = MomentumMLConfig(
            name="SimpleMomentumStrategy",
            description="Simple momentum strategy with RSI",
            rsi_period=rsi_period
        )
        super().__init__(config)
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.momentum_period = momentum_period

    @property
    def required_columns(self) -> List[str]:
        return ["close"]

    @property
    def min_periods(self) -> int:
        return max(self.rsi_period, self.momentum_period) + 5

    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Compute simple momentum signals.
        """
        close = data["close"]
        
        rsi = calculate_rsi(close, period=self.rsi_period)
        momentum = close.pct_change(self.momentum_period)
        
        self._indicators["rsi"] = rsi
        self._indicators["momentum"] = momentum

        signals = np.zeros(len(data))
        
        in_position = False
        
        for i in range(self.min_periods, len(data)):
            current_rsi = rsi.iloc[i]
            current_momentum = momentum.iloc[i]
            
            if not in_position:
                if current_rsi < self.rsi_oversold and current_momentum < 0:
                    signals[i] = 1
                    in_position = True
            else:
                if current_rsi > self.rsi_overbought:
                    signals[i] = -1
                    in_position = False

        return signals
