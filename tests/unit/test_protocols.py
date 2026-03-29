"""
Tests for protocols module.
"""

import pytest
from typing import Any, List
from trading_system.protocols import (
    DataFetcher,
    DataValidator,
    Strategy,
    MetricsCalculator,
    BacktestEngine,
    Optimizer,
)
import pandas as pd
import numpy as np


class MockDataFetcher:
    """Mock implementation of DataFetcher for testing."""
    
    def __init__(self, data=None):
        self.data = data
        self.fetch_called = False
    
    async def fetch_historical(
        self,
        symbol: str,
        start_date: Any,
        end_date: Any,
        interval: str = "1d"
    ):
        self.fetch_called = True
        return self.data


class MockDataValidator:
    """Mock implementation of DataValidator for testing."""
    
    def __init__(self, is_valid: bool = True):
        self.is_valid = is_valid
        self.validate_called = False
    
    def validate(self, data: Any) -> bool:
        self.validate_called = True
        return self.is_valid


class MockStrategy:
    """Mock implementation of Strategy for testing."""
    
    def __init__(self, name: str = "MockStrategy"):
        self._name = name
    
    @property
    def name(self) -> str:
        return self._name
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        return pd.Series([0] * len(data), index=data.index)


class TestDataFetcherProtocol:
    """Test DataFetcher protocol."""

    def test_data_fetcher_protocol(self):
        """Test that DataFetcher protocol is properly defined."""
        fetcher = MockDataFetcher(data=pd.DataFrame())
        
        assert hasattr(fetcher, 'fetch_historical')
        assert callable(fetcher.fetch_historical)

    @pytest.mark.asyncio
    async def test_fetch_historical_call(self):
        """Test fetch_historical method call."""
        dates = pd.date_range('2023-01-01', periods=10)
        data = pd.DataFrame({
            'open': np.random.rand(10) * 100 + 100,
            'high': np.random.rand(10) * 100 + 100,
            'low': np.random.rand(10) * 100 + 100,
            'close': np.random.rand(10) * 100 + 100,
            'volume': np.random.randint(1000, 10000, 10)
        }, index=dates)
        
        fetcher = MockDataFetcher(data=data)
        result = await fetcher.fetch_historical("AAPL", "2023-01-01", "2023-12-31")
        
        assert fetcher.fetch_called is True
        assert len(result) == 10


class TestDataValidatorProtocol:
    """Test DataValidator protocol."""

    def test_data_validator_protocol(self):
        """Test that DataValidator protocol is properly defined."""
        validator = MockDataValidator()
        
        assert hasattr(validator, 'validate')
        assert callable(validator.validate)

    def test_validate_returns_bool(self):
        """Test validate returns boolean."""
        validator = MockDataValidator(is_valid=True)
        result = validator.validate({})
        
        assert isinstance(result, bool)
        assert result is True


class TestStrategyProtocol:
    """Test Strategy protocol."""

    def test_strategy_protocol(self):
        """Test that Strategy protocol is properly defined."""
        strategy = MockStrategy()
        
        assert hasattr(strategy, 'name')
        assert hasattr(strategy, 'generate_signals')

    def test_generate_signals(self):
        """Test generate_signals method."""
        dates = pd.date_range('2023-01-01', periods=10)
        data = pd.DataFrame({
            'close': np.random.rand(10) * 100
        }, index=dates)
        
        strategy = MockStrategy("TestStrategy")
        result = strategy.generate_signals(data)
        
        assert len(result) == 10
        assert strategy.name == "TestStrategy"


class TestMetricsCalculatorProtocol:
    """Test MetricsCalculator protocol."""

    def test_metrics_calculator_protocol(self):
        """Test that MetricsCalculator protocol is properly defined."""
        
        class MockMetricsCalculator(MetricsCalculator):
            def calculate_returns(self, trades: pd.DataFrame) -> dict:
                return {"total_return": 0.0}
            
            def calculate_risk(self, trades: pd.DataFrame) -> dict:
                return {"max_drawdown": 0.0}
            
            def calculate_ratios(self, trades: pd.DataFrame) -> dict:
                return {"sharpe": 0.0}
        
        calc = MockMetricsCalculator()
        
        assert hasattr(calc, 'calculate_returns')
        assert hasattr(calc, 'calculate_risk')
        assert hasattr(calc, 'calculate_ratios')


class TestBacktestEngineProtocol:
    """Test BacktestEngine protocol."""

    def test_backtest_engine_protocol(self):
        """Test that BacktestEngine protocol is properly defined."""
        
        class MockBacktestEngine(BacktestEngine):
            def run(self, strategy: Strategy, data: pd.DataFrame, initial_capital: float = 100000.0) -> dict:
                return {}
            
            def get_trades(self) -> pd.DataFrame:
                return pd.DataFrame()
            
            def get_equity_curve(self) -> pd.DataFrame:
                return pd.DataFrame()
        
        engine = MockBacktestEngine()
        
        assert hasattr(engine, 'run')
        assert hasattr(engine, 'get_trades')
        assert hasattr(engine, 'get_equity_curve')


class TestOptimizerProtocol:
    """Test Optimizer protocol."""

    def test_optimizer_protocol(self):
        """Test that Optimizer protocol is properly defined."""
        
        class MockOptimizer(Optimizer):
            def optimize(self, strategy_class: type, data: pd.DataFrame, param_grid: dict) -> dict:
                return {}
            
            def get_results(self) -> dict:
                return {}
        
        optimizer = MockOptimizer()
        
        assert hasattr(optimizer, 'optimize')
        assert hasattr(optimizer, 'get_results')


class TestProtocolIntegration:
    """Integration tests for protocols."""

    @pytest.mark.asyncio
    async def test_data_pipeline(self):
        """Test complete data pipeline with protocols."""
        dates = pd.date_range('2023-01-01', periods=100)
        data = pd.DataFrame({
            'open': np.random.rand(100) * 100 + 100,
            'high': np.random.rand(100) * 100 + 100,
            'low': np.random.rand(100) * 100 + 100,
            'close': np.random.rand(100) * 100 + 100,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        fetcher = MockDataFetcher(data=data)
        validator = MockDataValidator(is_valid=True)
        
        fetched_data = await fetcher.fetch_historical("AAPL", "2023-01-01", "2023-12-31")
        is_valid = validator.validate(fetched_data)
        
        assert is_valid is True
        assert len(fetched_data) == 100
