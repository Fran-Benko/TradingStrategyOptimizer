"""
Pytest configuration for integration tests.

Provides shared fixtures and configuration for all integration tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# =============================================================================
# Common Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_seed():
    """Seed for reproducible tests."""
    return 42


@pytest.fixture(scope="session")
def base_date():
    """Base date for test data generation."""
    return datetime(2023, 1, 1)


@pytest.fixture
def sample_ohlcv_generator(test_seed):
    """Factory for generating sample OHLCV data."""
    def _generate(start_date, periods, freq="D", base_price=100, volatility=0.02):
        """Generate OHLCV data with specified parameters."""
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        dates = pd.date_range(start=start_date, periods=periods, freq=freq)
        np.random.seed(test_seed)
        
        returns = np.random.normal(0.0003, volatility, periods)
        prices = base_price * (1 + returns).cumprod()
        
        return pd.DataFrame({
            "open": prices * (1 + np.random.uniform(-0.005, 0.005, periods)),
            "high": prices * (1 + np.abs(np.random.uniform(0.005, 0.02, periods))),
            "low": prices * (1 - np.abs(np.random.uniform(0.005, 0.02, periods))),
            "close": prices,
            "volume": np.random.randint(5_000_000, 25_000_000, periods)
        }, index=dates)
    
    return _generate


@pytest.fixture
def trending_data(sample_ohlcv_generator):
    """Generate trending OHLCV data."""
    return sample_ohlcv_generator(
        start_date="2023-01-01",
        periods=200,
        volatility=0.01
    )


@pytest.fixture
def volatile_data(sample_ohlcv_generator):
    """Generate high volatility OHLCV data."""
    return sample_ohlcv_generator(
        start_date="2023-01-01",
        periods=200,
        volatility=0.03
    )


@pytest.fixture
def oscillating_data():
    """Generate oscillating OHLCV data for mean reversion testing."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    
    t = np.linspace(0, 4 * np.pi, 200)
    wave = 30 * np.sin(t)
    noise = np.random.randn(200) * 3
    prices = 100 + wave + noise
    
    return pd.DataFrame({
        "open": prices + np.random.randn(200) * 0.5,
        "high": prices + abs(np.random.randn(200)) * 2,
        "low": prices - abs(np.random.randn(200)) * 2,
        "close": prices,
        "volume": np.random.randint(5_000_000, 25_000_000, 200)
    }, index=dates)


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def default_trading_config():
    """Default trading configuration."""
    return {
        "initial_capital": 100000.0,
        "commission": 0.001,
        "slippage": 0.0005,
        "position_size": 1.0,
        "risk_free_rate": 0.0,
    }


@pytest.fixture
def default_optimization_config():
    """Default optimization configuration."""
    return {
        "metric": "sharpe_ratio",
        "maximize": True,
        "min_trades_per_fold": 5,
        "verbose": False,
        "seed": 42,
    }


@pytest.fixture
def default_walk_forward_config():
    """Default walk-forward configuration."""
    return {
        "window_type": "rolling",
        "train_window": 200,
        "test_window": 50,
        "step_size": 50,
    }


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    for item in items:
        # Mark all integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark slow tests
        if "walk_forward" in item.name or "long_term" in item.name:
            item.add_marker(pytest.mark.slow)
