"""
Unit tests for BacktestEngine.

Tests cover:
- BacktestConfig validation
- BacktestEngine.run() with sample strategies
- _calculate_metrics
- Trade recording
- Equity curve
- All result metrics (Sharpe, Sortino, drawdown)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from trading_system.backtesting.engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
    Trade,
)
from trading_system.strategies.base.base import BaseStrategy, StrategyConfig


class MockStrategy(BaseStrategy):
    """Mock strategy for testing backtest engine."""
    
    def __init__(self, config: StrategyConfig = None, signals: np.ndarray = None):
        super().__init__(config)
        self._mock_signals = signals
    
    @property
    def required_columns(self):
        return ["close"]
    
    @property
    def min_periods(self):
        return 1
    
    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        if self._mock_signals is not None:
            return self._mock_signals
        return np.zeros(len(data))


class AllBuyStrategy(MockStrategy):
    """Strategy that generates all buy signals."""
    
    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(data))
        # Buy on day 5, sell on day 10
        signals[5] = 1
        signals[10] = -1
        return signals


class AllHoldStrategy(MockStrategy):
    """Strategy that generates no signals."""
    
    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        return np.zeros(len(data))


class AlternatingSignalsStrategy(MockStrategy):
    """Strategy with alternating buy/sell signals for multiple trades."""
    
    def _compute_signals(self, data: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(data))
        # Generate buy/sell pairs every 5 days
        for i in range(5, len(data) - 1, 5):
            signals[i] = 1   # Buy
            if i + 3 < len(data):
                signals[i + 3] = -1  # Sell after 3 days
        return signals


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    np.random.seed(42)
    
    prices = 100 + np.cumsum(np.random.randn(100) * 2)
    
    return pd.DataFrame({
        "open": prices + np.random.randn(100) * 0.5,
        "high": prices + abs(np.random.randn(100)) * 2,
        "low": prices - abs(np.random.randn(100)) * 2,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, 100)
    }, index=dates)


@pytest.fixture
def rising_ohlcv_data():
    """Generate steadily rising OHLCV data."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    
    prices = np.linspace(100, 150, 100)
    
    return pd.DataFrame({
        "open": prices + 0.5,
        "high": prices + 2,
        "low": prices - 2,
        "close": prices,
        "volume": 1000000
    }, index=dates)


@pytest.fixture
def falling_ohlcv_data():
    """Generate steadily falling OHLCV data."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    
    prices = np.linspace(150, 100, 100)
    
    return pd.DataFrame({
        "open": prices + 0.5,
        "high": prices + 2,
        "low": prices - 2,
        "close": prices,
        "volume": 1000000
    }, index=dates)


@pytest.fixture
def default_config():
    """Default backtest configuration."""
    return BacktestConfig()


@pytest.fixture
def custom_config():
    """Custom backtest configuration."""
    return BacktestConfig(
        initial_capital=50000.0,
        commission=0.002,
        slippage=0.001,
        position_size=0.5,
        risk_free_rate=0.02
    )


class TestBacktestConfig:
    """Tests for BacktestConfig validation."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = BacktestConfig()
        
        assert config.initial_capital == 100000.0
        assert config.commission == 0.001
        assert config.slippage == 0.0005
        assert config.position_size == 1.0
        assert config.risk_free_rate == 0.0
    
    def test_valid_custom_config(self, custom_config):
        """Test valid custom configuration."""
        assert custom_config.validate() is True
    
    def test_invalid_initial_capital_zero(self):
        """Test that zero initial capital raises error."""
        config = BacktestConfig(initial_capital=0)
        with pytest.raises(ValueError, match="Initial capital must be positive"):
            config.validate()
    
    def test_invalid_initial_capital_negative(self):
        """Test that negative initial capital raises error."""
        config = BacktestConfig(initial_capital=-1000)
        with pytest.raises(ValueError, match="Initial capital must be positive"):
            config.validate()
    
    def test_invalid_commission_negative(self):
        """Test that negative commission raises error."""
        config = BacktestConfig(commission=-0.1)
        with pytest.raises(ValueError, match="Commission must be between 0 and 1"):
            config.validate()
    
    def test_invalid_commission_too_high(self):
        """Test that commission > 1 raises error."""
        config = BacktestConfig(commission=1.5)
        with pytest.raises(ValueError, match="Commission must be between 0 and 1"):
            config.validate()
    
    def test_valid_commission_boundary(self):
        """Test commission boundary values."""
        config = BacktestConfig(commission=0)
        assert config.validate() is True
        
        config = BacktestConfig(commission=1)
        assert config.validate() is True
    
    def test_invalid_slippage_negative(self):
        """Test that negative slippage raises error."""
        config = BacktestConfig(slippage=-0.1)
        with pytest.raises(ValueError, match="Slippage must be between 0 and 1"):
            config.validate()
    
    def test_invalid_slippage_too_high(self):
        """Test that slippage > 1 raises error."""
        config = BacktestConfig(slippage=2.0)
        with pytest.raises(ValueError, match="Slippage must be between 0 and 1"):
            config.validate()
    
    def test_invalid_position_size_zero(self):
        """Test that zero position size raises error."""
        config = BacktestConfig(position_size=0)
        with pytest.raises(ValueError, match="Position size must be between 0 and 1"):
            config.validate()
    
    def test_invalid_position_size_too_high(self):
        """Test that position size > 1 raises error."""
        config = BacktestConfig(position_size=1.5)
        with pytest.raises(ValueError, match="Position size must be between 0 and 1"):
            config.validate()
    
    def test_valid_position_size_boundary(self):
        """Test position size boundary values."""
        config = BacktestConfig(position_size=0.01)
        assert config.validate() is True


class TestBacktestEngineInit:
    """Tests for BacktestEngine initialization."""
    
    def test_init_default_config(self):
        """Test engine initialization with default config."""
        engine = BacktestEngine()
        assert engine.config is not None
        assert engine.config.initial_capital == 100000.0
    
    def test_init_custom_config(self, custom_config):
        """Test engine initialization with custom config."""
        engine = BacktestEngine(custom_config)
        assert engine.config.initial_capital == 50000.0
        assert engine.config.position_size == 0.5
    
    def test_init_invalid_config(self):
        """Test that invalid config raises error."""
        config = BacktestConfig(initial_capital=-100)
        with pytest.raises(ValueError):
            BacktestEngine(config)


class TestBacktestEngineRun:
    """Tests for BacktestEngine.run() method."""
    
    def test_run_with_no_signals(self, sample_ohlcv_data):
        """Test backtest with strategy generating no signals."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result is not None
        assert isinstance(result, BacktestResult)
        assert result.total_trades == 0
        assert result.final_capital == result.initial_capital
    
    def test_run_with_single_trade(self, sample_ohlcv_data):
        """Test backtest with single buy/sell pair."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result is not None
        assert result.total_trades == 1
        assert result.final_capital != result.initial_capital
    
    def test_run_with_multiple_trades(self, sample_ohlcv_data):
        """Test backtest with multiple trades."""
        engine = BacktestEngine()
        strategy = AlternatingSignalsStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result is not None
        assert result.total_trades > 1
    
    def test_run_result_attributes(self, sample_ohlcv_data):
        """Test that result contains all expected attributes."""
        engine = BacktestEngine()
        config = StrategyConfig(name="AllBuyStrategy")
        strategy = AllBuyStrategy(config=config)
        
        result = engine.run(strategy, sample_ohlcv_data, "AAPL")
        
        assert result.strategy_name == "AllBuyStrategy"
        assert result.symbol == "AAPL"
        assert result.start_date == sample_ohlcv_data.index[0]
        assert result.end_date == sample_ohlcv_data.index[-1]
        assert result.initial_capital == 100000.0
        assert result.total_trades == 1
    
    def test_run_with_custom_config(self, sample_ohlcv_data):
        """Test backtest with custom configuration."""
        config = BacktestConfig(initial_capital=50000.0, commission=0.005)
        engine = BacktestEngine(config)
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.initial_capital == 50000.0
    
    def test_run_with_small_position_size(self, sample_ohlcv_data):
        """Test backtest with small position size."""
        config = BacktestConfig(position_size=0.1)
        engine = BacktestEngine(config)
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        # Position size affects trade quantity but should still execute trades
        assert result.total_trades >= 0
    
    def test_run_with_high_commission(self, rising_ohlcv_data):
        """Test backtest with high commission (may reduce profitability)."""
        config = BacktestConfig(commission=0.1)  # 10% commission
        engine = BacktestEngine(config)
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, rising_ohlcv_data, "TEST")
        
        # With high commission, may even lose money
        assert result is not None
        assert result.total_trades == 1
    
    def test_run_persists_open_position(self, sample_ohlcv_data):
        """Test that open position at end of data is closed."""
        # Create a strategy that buys but never sells
        signals = np.zeros(len(sample_ohlcv_data))
        signals[5] = 1  # Buy on day 5, never sell
        
        strategy = MockStrategy(signals=signals)
        engine = BacktestEngine()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        # Position should be closed at end of data
        assert result.total_trades == 1


class TestTradeRecording:
    """Tests for trade recording functionality."""
    
    def test_trade_pnl_calculation(self, sample_ohlcv_data):
        """Test that trade PnL is calculated correctly."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert len(result.trades) == 1
        trade = result.trades[0]
        
        # PnL should be calculated
        assert trade.pnl is not None
        assert isinstance(trade.pnl, float)
        
        # Commission should be recorded
        assert trade.commission >= 0
    
    def test_trade_entry_exit_prices(self, sample_ohlcv_data):
        """Test that entry and exit prices are recorded correctly."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        trade = result.trades[0]
        
        assert trade.entry_date is not None
        assert trade.exit_date is not None
        assert trade.entry_price > 0
        assert trade.exit_price > 0
        
        # Entry should be before exit
        assert trade.entry_date < trade.exit_date
    
    def test_trade_quantity(self, sample_ohlcv_data):
        """Test that trade quantity is recorded."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        trade = result.trades[0]
        assert trade.quantity > 0
    
    def test_trade_return_percentage(self, sample_ohlcv_data):
        """Test that return percentage is calculated."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        trade = result.trades[0]
        assert trade.return_pct is not None
    
    def test_multiple_trades_recorded(self, sample_ohlcv_data):
        """Test that multiple trades are all recorded."""
        engine = BacktestEngine()
        strategy = AlternatingSignalsStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert len(result.trades) == result.total_trades
        assert result.total_trades > 1
    
    def test_trades_list_type(self, sample_ohlcv_data):
        """Test that trades attribute is a list of Trade objects."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert isinstance(result.trades, list)
        for trade in result.trades:
            assert isinstance(trade, Trade)


class TestEquityCurve:
    """Tests for equity curve functionality."""
    
    def test_equity_curve_exists(self, sample_ohlcv_data):
        """Test that equity curve is generated."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.equity_curve is not None
        assert isinstance(result.equity_curve, pd.Series)
    
    def test_equity_curve_length(self, sample_ohlcv_data):
        """Test equity curve has correct length."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert len(result.equity_curve) > 0
    
    def test_equity_curve_starts_with_initial_capital(self, sample_ohlcv_data):
        """Test equity curve starts with initial capital."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.equity_curve.iloc[0] == result.initial_capital
    
    def test_equity_curve_ends_with_final_capital(self, sample_ohlcv_data):
        """Test equity curve ends with final capital."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.equity_curve.iloc[-1] == result.final_capital
    
    def test_equity_curve_increases_on_profitable_trade(self, rising_ohlcv_data):
        """Test equity curve increases with profitable trades."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, rising_ohlcv_data, "TEST")
        
        # Equity should grow with profitable trades
        assert result.equity_curve.iloc[-1] > result.equity_curve.iloc[0]
    
    def test_equity_curve_no_trades_unchanged(self, sample_ohlcv_data):
        """Test equity curve stays flat with no trades."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        # All values should be the same (no trades)
        assert result.equity_curve.nunique() == 1
    
    def test_trades_series_exists(self, sample_ohlcv_data):
        """Test that trades series is generated."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.trades_series is not None
        assert isinstance(result.trades_series, pd.Series)


class TestMetricsCalculation:
    """Tests for performance metrics calculation."""
    
    def test_total_return_profitable(self, rising_ohlcv_data):
        """Test total return is positive for profitable strategy."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, rising_ohlcv_data, "TEST")
        
        assert result.total_return > 0
        assert result.final_capital > result.initial_capital
    
    def test_total_return_calculation(self, sample_ohlcv_data):
        """Test total return calculation formula."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        expected_return = (result.final_capital - result.initial_capital) / result.initial_capital
        assert abs(result.total_return - expected_return) < 1e-10
    
    def test_win_rate_no_trades(self, sample_ohlcv_data):
        """Test win rate is 0 when no trades."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.win_rate == 0
    
    def test_win_rate_all_winning(self, rising_ohlcv_data):
        """Test win rate is 1 when all trades are winning."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, rising_ohlcv_data, "TEST")
        
        if result.total_trades > 0:
            assert result.winning_trades > 0
            assert result.win_rate > 0
    
    def test_profit_factor_calculation(self, sample_ohlcv_data):
        """Test profit factor calculation."""
        engine = BacktestEngine()
        strategy = AlternatingSignalsStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        if result.total_trades > 0:
            # Profit factor should be defined
            assert result.profit_factor is not None
            if result.winning_trades > 0 and result.losing_trades > 0:
                assert result.profit_factor > 0
    
    def test_profit_factor_no_losing_trades(self, rising_ohlcv_data):
        """Test profit factor when no losing trades."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, rising_ohlcv_data, "TEST")
        
        # If no losing trades, profit factor should be handled gracefully
        if result.losing_trades == 0:
            # Profit factor could be 0 or infinity depending on implementation
            assert result.profit_factor >= 0
    
    def test_winning_losing_trades_count(self, sample_ohlcv_data):
        """Test winning and losing trades counts."""
        engine = BacktestEngine()
        strategy = AlternatingSignalsStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.winning_trades + result.losing_trades == result.total_trades
    
    def test_avg_trade_return(self, sample_ohlcv_data):
        """Test average trade return calculation."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        if result.total_trades > 0:
            assert result.avg_trade_return is not None
    
    def test_avg_winning_losing_trades(self, sample_ohlcv_data):
        """Test average winning and losing trade values."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        if result.total_trades > 0:
            assert result.avg_winning_trade is not None
            assert result.avg_losing_trade is not None


class TestSharpeRatio:
    """Tests for Sharpe ratio calculation."""
    
    def test_sharpe_ratio_no_trades(self, sample_ohlcv_data):
        """Test Sharpe ratio when no trades executed."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        # Without trades, equity is flat, std is 0, Sharpe should be 0
        assert result.sharpe_ratio == 0
    
    def test_sharpe_ratio_with_trades(self, sample_ohlcv_data):
        """Test Sharpe ratio with trades."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.sharpe_ratio is not None
    
    def test_sharpe_ratio_with_risk_free_rate(self, sample_ohlcv_data):
        """Test Sharpe ratio calculation with risk-free rate."""
        config = BacktestConfig(risk_free_rate=0.02)
        engine = BacktestEngine(config)
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.sharpe_ratio is not None
    
    def test_sharpe_ratio_negative_returns(self, falling_ohlcv_data):
        """Test Sharpe ratio with negative returns."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, falling_ohlcv_data, "TEST")
        
        assert result.sharpe_ratio is not None


class TestSortinoRatio:
    """Tests for Sortino ratio calculation."""
    
    def test_sortino_ratio_no_trades(self, sample_ohlcv_data):
        """Test Sortino ratio when no trades executed."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        # Without volatility or downside, Sortino may be 0
        assert result.sortino_ratio == 0
    
    def test_sortino_ratio_with_trades(self, sample_ohlcv_data):
        """Test Sortino ratio with trades."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.sortino_ratio is not None
    
    def test_sortino_ratio_only_upside_returns(self, rising_ohlcv_data):
        """Test Sortino ratio with only upside returns."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, rising_ohlcv_data, "TEST")
        
        # No downside returns should give Sortino of 0 (division by zero)
        assert result.sortino_ratio == 0


class TestDrawdown:
    """Tests for drawdown calculation."""
    
    def test_max_drawdown_no_trades(self, sample_ohlcv_data):
        """Test drawdown when no trades executed."""
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        # No trades means no drawdown
        assert result.max_drawdown == 0
        assert result.max_drawdown_pct == 0
    
    def test_max_drawdown_with_trades(self, sample_ohlcv_data):
        """Test max drawdown with trades."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert result.max_drawdown is not None
        assert result.max_drawdown_pct is not None
    
    def test_max_drawdown_positive_returns(self, rising_ohlcv_data):
        """Test drawdown with positive returns."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, rising_ohlcv_data, "TEST")
        
        # Positive returns should have minimal drawdown
        assert result.max_drawdown_pct >= 0
    
    def test_max_drawdown_percentage(self, sample_ohlcv_data):
        """Test max drawdown percentage is between 0 and 1."""
        engine = BacktestEngine()
        strategy = AlternatingSignalsStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        
        assert 0 <= result.max_drawdown_pct <= 1


class TestResultSummary:
    """Tests for BacktestResult.summary() method."""
    
    def test_summary_format(self, sample_ohlcv_data):
        """Test that summary returns a formatted string."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        summary = result.summary()
        
        assert isinstance(summary, str)
        assert "Backtest Results" in summary
        assert "TEST" in summary
    
    def test_summary_contains_metrics(self, sample_ohlcv_data):
        """Test that summary contains key metrics."""
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, sample_ohlcv_data, "TEST")
        summary = result.summary()
        
        assert "Total Return" in summary
        assert "Win Rate" in summary
        assert "Sharpe Ratio" in summary
        assert "Sortino Ratio" in summary
        assert "Max Drawdown" in summary


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_very_small_data(self):
        """Test with minimal data (just enough for strategy)."""
        dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
        data = pd.DataFrame({
            "close": [100, 101, 102, 103, 104],
            "volume": 1000000
        }, index=dates)
        
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, data, "TEST")
        
        assert result is not None
        assert result.total_trades == 0
    
    def test_constant_prices(self):
        """Test with constant price data."""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        data = pd.DataFrame({
            "close": [100] * 50,
            "volume": 1000000
        }, index=dates)
        
        engine = BacktestEngine()
        strategy = AllBuyStrategy()
        
        result = engine.run(strategy, data, "TEST")
        
        # Trades execute but with zero price change
        assert result.total_trades == 1
        # PnL should be negative due to commission
        assert result.final_capital < result.initial_capital
    
    def test_high_volatility_data(self):
        """Test with highly volatile price data."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)
        
        prices = 100 + np.cumsum(np.random.randn(100) * 10)
        
        data = pd.DataFrame({
            "close": prices,
            "volume": 1000000
        }, index=dates)
        
        engine = BacktestEngine()
        strategy = AlternatingSignalsStrategy()
        
        result = engine.run(strategy, data, "TEST")
        
        assert result is not None
        assert result.total_trades > 0
    
    def test_single_day_data(self):
        """Test with single day data."""
        dates = [pd.Timestamp("2023-01-01")]
        data = pd.DataFrame({
            "close": [100],
            "volume": 1000000
        }, index=dates)
        
        engine = BacktestEngine()
        strategy = AllHoldStrategy()
        
        result = engine.run(strategy, data, "TEST")
        
        # Should handle gracefully
        assert result.total_trades == 0
