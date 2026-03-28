"""
Pytest configuration and shared fixtures.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


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
def sample_data_dict():
    """Generate sample data as dict for multiple symbols."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    np.random.seed(42)
    
    base = 100 + np.cumsum(np.random.randn(100) * 2)
    
    return {
        "AAPL": pd.DataFrame({
            "open": base + 0.5,
            "high": base + 2,
            "low": base - 2,
            "close": base,
            "volume": 1000000
        }, index=dates),
        "GOOGL": pd.DataFrame({
            "open": base * 1.5 + 0.5,
            "high": base * 1.5 + 2,
            "low": base * 1.5 - 2,
            "close": base * 1.5,
            "volume": 500000
        }, index=dates)
    }


@pytest.fixture
def mock_cache():
    """Create a mock cache for testing."""
    from trading_system.data.storage import InMemoryCache
    return InMemoryCache(max_size=10)


@pytest.fixture
def mock_rate_limiter():
    """Create a mock rate limiter for testing."""
    from trading_system.data.storage import RateLimiter
    return RateLimiter(max_requests=1000, window_seconds=60)
