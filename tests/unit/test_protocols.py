"""
Tests for protocols module.
"""

import pytest
from typing import Any, List, Optional
from trading_system.protocols import (
    DataFetcher,
    DataValidator,
    Strategy,
    Signal,
    SignalType,
    MetricsCalculator,
    BacktestEngineProto,
    Optimizer,
)


class MockDataFetcher(DataFetcher):
    """Mock implementation of DataFetcher for testing."""
    
    def __init__(self, data=None):
        self.data = data
        self.fetch_called = False
    
    async def fetch_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str = "1d"
    ):
        self.fetch_called = True
        return self.data


class MockDataValidator(DataValidator):
    """Mock implementation of DataValidator for testing."""
    
    def __init__(self, is_valid: bool = True):
        self.is_valid = is_valid
        self.validate_called = False
    
    def validate(self, data: Any) -> bool:
        self.validate_called = True
        return self.is_valid


class MockStrategy(Strategy):
    """Mock implementation of Strategy for testing."""
    
    def __init__(self, signals: List[Signal] = None):
        self.signals = signals or []
        self.generate_signals_called = False
    
    @property
    def name(self) -> str:
        return "MockStrategy"
    
    def generate_signals(self, data: Any) -> List[Signal]:
        self.generate_signals_called = True
        return self.signals


class TestDataFetcherProtocol:
    """Test DataFetcher protocol."""

    def test_data_fetcher_protocol(self):
        """Test that DataFetcher protocol is properly defined."""
        fetcher = MockDataFetcher(data=[])
        
        assert hasattr(fetcher, 'fetch_historical')
        assert callable(fetcher.fetch_historical)

    @pytest.mark.asyncio
    async def test_fetch_historical_call(self):
        """Test fetch_historical method call."""
        import pandas as pd
        import numpy as np
        
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

    def test_validate_called(self):
        """Test validate is called."""
        validator = MockDataValidator()
        validator.validate({})
        
        assert validator.validate_called is True


class TestStrategyProtocol:
    """Test Strategy protocol."""

    def test_strategy_protocol(self):
        """Test that Strategy protocol is properly defined."""
        strategy = MockStrategy()
        
        assert hasattr(strategy, 'name')
        assert hasattr(strategy, 'generate_signals')

    def test_generate_signals(self):
        """Test generate_signals method."""
        signals = [
            Signal(date=None, type=SignalType.BUY, price=100.0),
            Signal(date=None, type=SignalType.SELL, price=105.0),
        ]
        
        strategy = MockStrategy(signals=signals)
        result = strategy.generate_signals({})
        
        assert strategy.generate_signals_called is True
        assert len(result) == 2
        assert result[0].type == SignalType.BUY


class TestSignalType:
    """Test SignalType enum."""

    def test_signal_types(self):
        """Test all signal types exist."""
        assert SignalType.BUY is not None
        assert SignalType.SELL is not None
        assert SignalType.HOLD is not None

    def test_signal_type_values(self):
        """Test signal type values."""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"


class TestMetricsCalculatorProtocol:
    """Test MetricsCalculator protocol."""

    def test_metrics_calculator_protocol(self):
        """Test that MetricsCalculator protocol is properly defined."""
        
        class MockMetricsCalculator(MetricsCalculator):
            def calculate(self, data: Any) -> dict:
                return {}
        
        calc = MockMetricsCalculator()
        
        assert hasattr(calc, 'calculate')
        assert callable(calc.calculate)


class TestBacktestEngineProtocol:
    """Test BacktestEngineProto protocol."""

    def test_backtest_engine_protocol(self):
        """Test that BacktestEngineProto protocol is properly defined."""
        
        class MockBacktestEngine(BacktestEngineProto):
            def run(self, strategy: Strategy, data: Any) -> Any:
                return {}
        
        engine = MockBacktestEngine()
        
        assert hasattr(engine, 'run')
        assert callable(engine.run)


class TestOptimizerProtocol:
    """Test Optimizer protocol."""

    def test_optimizer_protocol(self):
        """Test that Optimizer protocol is properly defined."""
        
        class MockOptimizer(Optimizer):
            def optimize(self, strategy: Strategy, data: Any, params: dict) -> Any:
                return {}
        
        optimizer = MockOptimizer()
        
        assert hasattr(optimizer, 'optimize')
        assert callable(optimizer.optimize)


class TestProtocolIntegration:
    """Integration tests for protocols."""

    @pytest.mark.asyncio
    async def test_data_pipeline(self):
        """Test complete data pipeline with protocols."""
        import pandas as pd
        import numpy as np
        
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
