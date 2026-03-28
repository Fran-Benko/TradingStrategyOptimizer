"""
Backtesting engine.

Provides functionality for backtesting trading strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from trading_system.strategies.base import BaseStrategy, Signal, SignalType


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    initial_capital: float = 100000.0
    commission: float = 0.001
    slippage: float = 0.0005
    position_size: float = 1.0
    risk_free_rate: float = 0.0

    def validate(self) -> bool:
        """Validate backtest configuration."""
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        if not 0 <= self.commission <= 1:
            raise ValueError("Commission must be between 0 and 1")
        if not 0 <= self.slippage <= 1:
            raise ValueError("Slippage must be between 0 and 1")
        if not 0 < self.position_size <= 1:
            raise ValueError("Position size must be between 0 and 1")
        return True


@dataclass
class Trade:
    """Represents a single trade."""
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    quantity: float
    side: str
    pnl: float
    return_pct: float
    commission: float


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    strategy_name: str
    symbol: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    avg_trade_return: float
    avg_winning_trade: float
    avg_losing_trade: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    trades_series: pd.Series = field(default_factory=pd.Series)

    def summary(self) -> str:
        """Generate summary string."""
        return f"""
=== Backtest Results: {self.strategy_name} ===
Symbol: {self.symbol}
Period: {self.start_date.date()} to {self.end_date.date()}

Performance:
  Total Return: {self.total_return:.2%}
  Final Capital: ${self.final_capital:,.2f}
  Max Drawdown: {self.max_drawdown_pct:.2%}

Trading:
  Total Trades: {self.total_trades}
  Win Rate: {self.win_rate:.2%}
  Profit Factor: {self.profit_factor:.2f}

Risk-Adjusted:
  Sharpe Ratio: {self.sharpe_ratio:.2f}
  Sortino Ratio: {self.sortino_ratio:.2f}
"""


class BacktestEngine:
    """
    Backtesting engine for trading strategies.

    Simulates trading a strategy on historical data with
    realistic transaction costs and position management.

    Args:
        config: Backtest configuration

    Example:
        >>> config = BacktestConfig(initial_capital=100000)
        >>> engine = BacktestEngine(config)
        >>> result = engine.run(strategy, data, "AAPL")
        >>> print(result.summary())
    """

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.config.validate()

    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str
    ) -> BacktestResult:
        """
        Run backtest on historical data.

        Args:
            strategy: Trading strategy to test
            data: Historical OHLCV data
            symbol: Symbol being traded

        Returns:
            BacktestResult with performance metrics
        """
        signals = strategy.generate_signals(data)

        equity = [self.config.initial_capital]
        trades: List[Trade] = []
        position = 0
        entry_price = 0.0
        entry_date = None
        trade_returns = []

        for i in range(1, len(data)):
            current_price = data["close"].iloc[i]
            current_date = data.index[i]
            signal = signals[i]

            if signal == 1 and position == 0:
                position_value = equity[-1] * self.config.position_size
                shares = int(position_value / current_price)
                
                if shares > 0:
                    execution_price = current_price * (1 + self.config.slippage)
                    commission = execution_price * shares * self.config.commission
                    
                    position = shares
                    entry_price = execution_price
                    entry_date = current_date

            elif signal == -1 and position > 0:
                execution_price = current_price * (1 - self.config.slippage)
                commission = execution_price * position * self.config.commission
                
                pnl = (execution_price - entry_price) * position - commission
                return_pct = (execution_price - entry_price) / entry_price

                trade_returns.append(return_pct)

                trades.append(Trade(
                    entry_date=entry_date,
                    exit_date=current_date,
                    entry_price=entry_price,
                    exit_price=execution_price,
                    quantity=position,
                    side="long",
                    pnl=pnl,
                    return_pct=return_pct,
                    commission=commission
                ))

                equity.append(equity[-1] + pnl)
                position = 0

            else:
                if position > 0:
                    unrealized_pnl = (current_price - entry_price) * position
                    equity.append(equity[-1] + unrealized_pnl)
                else:
                    equity.append(equity[-1])

        if position > 0:
            final_price = data["close"].iloc[-1]
            execution_price = final_price * (1 - self.config.slippage)
            commission = execution_price * position * self.config.commission
            pnl = (execution_price - entry_price) * position - commission

            trades.append(Trade(
                entry_date=entry_date,
                exit_date=data.index[-1],
                entry_price=entry_price,
                exit_price=execution_price,
                quantity=position,
                side="long",
                pnl=pnl,
                return_pct=(execution_price - entry_price) / entry_price,
                commission=commission
            ))
            equity[-1] = equity[-1] + pnl

        equity_curve = pd.Series(equity, index=data.index[-len(equity):])

        return self._calculate_metrics(
            strategy.name,
            symbol,
            data.index[0],
            data.index[-1],
            equity_curve,
            trades,
            data["close"]
        )

    def _calculate_metrics(
        self,
        strategy_name: str,
        symbol: str,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        equity_curve: pd.Series,
        trades: List[Trade],
        prices: pd.Series
    ) -> BacktestResult:
        """Calculate performance metrics."""
        initial_capital = self.config.initial_capital
        final_capital = equity_curve.iloc[-1]

        total_return = (final_capital - initial_capital) / initial_capital

        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]

        win_rate = len(winning_trades) / len(trades) if trades else 0

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        returns = equity_curve.pct_change().dropna()
        sharpe_ratio = self._sharpe_ratio(returns)
        sortino_ratio = self._sortino_ratio(returns)

        cumulative = (1 + returns).cumprod() - 1
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_drawdown = drawdown.min()
        max_drawdown_pct = abs(max_drawdown)

        avg_trade_return = np.mean([t.return_pct for t in trades]) if trades else 0
        avg_winning = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_losing = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            avg_trade_return=avg_trade_return,
            avg_winning_trade=avg_winning,
            avg_losing_trade=avg_losing,
            trades=trades,
            equity_curve=equity_curve,
            trades_series=pd.Series([t.pnl for t in trades])
        )

    def _sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        excess_returns = returns - self.config.risk_free_rate / 252
        return np.sqrt(252) * excess_returns.mean() / returns.std()

    def _sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio."""
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - self.config.risk_free_rate / 252
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        return np.sqrt(252) * excess_returns.mean() / downside_returns.std()
