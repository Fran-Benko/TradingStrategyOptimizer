"""
Unit tests for technical indicators.
"""

import pytest
import pandas as pd
import numpy as np

from trading_system.strategies.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_stochastic,
    calculate_momentum,
    calculate_roc,
)


class TestCalculateRSI:
    """Tests for calculate_rsi function."""

    @pytest.fixture
    def sample_prices(self):
        """Generate sample price data."""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 2)
        return pd.Series(prices, index=dates)

    @pytest.fixture
    def sample_numpy_prices(self):
        """Generate sample price data as numpy array."""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 2)
        return prices

    def test_rsi_returns_series(self, sample_prices):
        """Test that RSI returns a pandas Series."""
        result = calculate_rsi(sample_prices)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)

    def test_rsi_default_period(self, sample_prices):
        """Test RSI with default period (14)."""
        result = calculate_rsi(sample_prices)

        assert result.iloc[-1] >= 0
        assert result.iloc[-1] <= 100

    def test_rsi_custom_period(self, sample_prices):
        """Test RSI with custom period."""
        result = calculate_rsi(sample_prices, period=20)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)

    def test_rsi_numpy_input(self, sample_numpy_prices):
        """Test RSI with numpy array input."""
        result = calculate_rsi(sample_numpy_prices)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_numpy_prices)

    def test_rsi_values_in_range(self, sample_prices):
        """Test that RSI values are between 0 and 100."""
        result = calculate_rsi(sample_prices)

        assert (result >= 0).all() or result[result.notna()].min() >= 0
        assert (result <= 100).all() or result[result.notna()].max() <= 100

    def test_rsi_short_data(self):
        """Test RSI with short data (less than period)."""
        prices = pd.Series([100, 101, 102, 103, 104])
        result = calculate_rsi(prices, period=14)

        assert len(result) == len(prices)
        assert not result.isna().all()

    def test_rsi_constant_prices(self):
        """Test RSI with constant prices."""
        prices = pd.Series([100] * 30)
        result = calculate_rsi(prices, period=14)

        assert isinstance(result, pd.Series)
        assert len(result) == len(prices)

    def test_rsi_trending_up(self):
        """Test RSI with strongly trending up prices."""
        prices = pd.Series(range(100, 200))
        result = calculate_rsi(prices, period=14)

        assert isinstance(result, pd.Series)
        valid_values = result[result.notna()]
        assert len(valid_values) > 0

    def test_rsi_trending_down(self):
        """Test RSI with strongly trending down prices."""
        prices = pd.Series(range(200, 100, -1))
        result = calculate_rsi(prices, period=14)

        assert isinstance(result, pd.Series)
        valid_values = result[result.notna()]
        assert len(valid_values) > 0

    def test_rsi_invalid_period_zero(self):
        """Test RSI with zero period raises error."""
        prices = pd.Series([100, 101, 102])
        with pytest.raises(Exception):
            calculate_rsi(prices, period=0)

    def test_rsi_invalid_period_negative(self):
        """Test RSI with negative period raises error."""
        prices = pd.Series([100, 101, 102])
        with pytest.raises(Exception):
            calculate_rsi(prices, period=-5)

    def test_rsi_empty_series(self):
        """Test RSI with empty series."""
        prices = pd.Series(dtype=float)
        result = calculate_rsi(prices, period=14)

        assert len(result) == 0

    def test_rsi_single_value(self):
        """Test RSI with single value."""
        prices = pd.Series([100.0])
        result = calculate_rsi(prices, period=14)

        assert len(result) == 1


class TestCalculateMACD:
    """Tests for calculate_macd function."""

    @pytest.fixture
    def sample_prices(self):
        """Generate sample price data."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        return pd.Series(prices, index=dates)

    @pytest.fixture
    def sample_numpy_prices(self):
        """Generate sample price data as numpy array."""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        return prices

    def test_macd_returns_dataframe(self, sample_prices):
        """Test that MACD returns a DataFrame."""
        result = calculate_macd(sample_prices)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_prices)

    def test_macd_default_columns(self, sample_prices):
        """Test MACD has required columns."""
        result = calculate_macd(sample_prices)

        assert "macd" in result.columns
        assert "signal" in result.columns
        assert "histogram" in result.columns

    def test_macd_default_periods(self, sample_prices):
        """Test MACD with default periods (12, 26, 9)."""
        result = calculate_macd(sample_prices)

        assert len(result) == len(sample_prices)
        assert "macd" in result.columns
        assert "signal" in result.columns
        assert "histogram" in result.columns

    def test_macd_numpy_input(self, sample_numpy_prices):
        """Test MACD with numpy array input."""
        result = calculate_macd(sample_numpy_prices)

        assert isinstance(result, pd.DataFrame)
        assert "macd" in result.columns
        assert "signal" in result.columns
        assert "histogram" in result.columns

    def test_macd_custom_periods(self, sample_prices):
        """Test MACD with custom periods."""
        result = calculate_macd(
            sample_prices,
            fast_period=8,
            slow_period=20,
            signal_period=5
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_prices)

    def test_macd_histogram_calculation(self, sample_prices):
        """Test MACD histogram is correctly calculated."""
        result = calculate_macd(sample_prices)

        expected_histogram = result["macd"] - result["signal"]
        pd.testing.assert_series_equal(
            result["histogram"].dropna(),
            expected_histogram.dropna(),
            check_names=False
        )

    def test_macd_short_data(self):
        """Test MACD with short data."""
        prices = pd.Series([100, 101, 102, 103, 104])
        result = calculate_macd(prices)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(prices)

    def test_macd_empty_series(self):
        """Test MACD with empty series."""
        prices = pd.Series(dtype=float)
        result = calculate_macd(prices)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestCalculateStochastic:
    """Tests for calculate_stochastic function."""

    @pytest.fixture
    def sample_ohlcv(self):
        """Generate sample OHLCV data."""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        np.random.seed(42)
        base = 100
        prices = [base]
        for _ in range(49):
            prices.append(prices[-1] + np.random.randn() * 2)

        return pd.DataFrame({
            "open": prices,
            "high": [p + abs(np.random.rand() * 2) for p in prices],
            "low": [p - abs(np.random.rand() * 2) for p in prices],
            "close": prices,
            "volume": np.random.randint(1000000, 5000000, 50)
        }, index=dates)

    def test_stochastic_returns_dataframe(self, sample_ohlcv):
        """Test that stochastic returns a DataFrame."""
        result = calculate_stochastic(
            sample_ohlcv["high"],
            sample_ohlcv["low"],
            sample_ohlcv["close"]
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_ohlcv)

    def test_stochastic_default_columns(self, sample_ohlcv):
        """Test stochastic has required columns."""
        result = calculate_stochastic(
            sample_ohlcv["high"],
            sample_ohlcv["low"],
            sample_ohlcv["close"]
        )

        assert "k" in result.columns
        assert "d" in result.columns

    def test_stochastic_default_periods(self, sample_ohlcv):
        """Test stochastic with default periods (14, 3)."""
        result = calculate_stochastic(
            sample_ohlcv["high"],
            sample_ohlcv["low"],
            sample_ohlcv["close"]
        )

        assert len(result) == len(sample_ohlcv)

    def test_stochastic_custom_periods(self, sample_ohlcv):
        """Test stochastic with custom periods."""
        result = calculate_stochastic(
            sample_ohlcv["high"],
            sample_ohlcv["low"],
            sample_ohlcv["close"],
            k_period=10,
            d_period=5
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_ohlcv)

    def test_stochastic_values_in_range(self, sample_ohlcv):
        """Test that stochastic values are between 0 and 100."""
        result = calculate_stochastic(
            sample_ohlcv["high"],
            sample_ohlcv["low"],
            sample_ohlcv["close"]
        )

        valid_k = result["k"][result["k"].notna()]
        valid_d = result["d"][result["d"].notna()]

        assert (valid_k >= 0).all()
        assert (valid_k <= 100).all()
        assert (valid_d >= 0).all()
        assert (valid_d <= 100).all()

    def test_stochastic_short_data(self):
        """Test stochastic with short data."""
        high = pd.Series([100, 101, 102, 103, 104])
        low = pd.Series([99, 100, 101, 102, 103])
        close = pd.Series([100, 101, 102, 103, 104])

        result = calculate_stochastic(high, low, close, k_period=14)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(high)

    def test_stochastic_flat_data(self):
        """Test stochastic with flat prices (no movement)."""
        high = pd.Series([100] * 20)
        low = pd.Series([100] * 20)
        close = pd.Series([100] * 20)

        result = calculate_stochastic(high, low, close, k_period=14)

        assert isinstance(result, pd.DataFrame)
        assert "k" in result.columns
        assert "d" in result.columns


class TestCalculateMomentum:
    """Tests for calculate_momentum function."""

    @pytest.fixture
    def sample_prices(self):
        """Generate sample price data."""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 2)
        return pd.Series(prices, index=dates)

    @pytest.fixture
    def sample_numpy_prices(self):
        """Generate sample price data as numpy array."""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 2)
        return prices

    def test_momentum_returns_series(self, sample_prices):
        """Test that momentum returns a pandas Series."""
        result = calculate_momentum(sample_prices)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)

    def test_momentum_default_period(self, sample_prices):
        """Test momentum with default period (10)."""
        result = calculate_momentum(sample_prices)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)

    def test_momentum_custom_period(self, sample_prices):
        """Test momentum with custom period."""
        result = calculate_momentum(sample_prices, period=5)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)

    def test_momentum_numpy_input(self, sample_numpy_prices):
        """Test momentum with numpy array input."""
        result = calculate_momentum(sample_numpy_prices)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_numpy_prices)

    def test_momentum_calculation(self):
        """Test momentum calculation is correct."""
        prices = pd.Series([100, 102, 101, 103, 105, 107, 106, 108, 110, 112])
        result = calculate_momentum(prices, period=1)

        expected = prices.diff(1)
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_momentum_longer_period(self):
        """Test momentum with period > 1."""
        prices = pd.Series([100, 102, 104, 103, 105, 107, 109, 108, 110, 112])
        result = calculate_momentum(prices, period=3)

        expected = prices.diff(3)
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_momentum_short_data(self):
        """Test momentum with short data."""
        prices = pd.Series([100, 101, 102])
        result = calculate_momentum(prices, period=10)

        assert isinstance(result, pd.Series)
        assert len(result) == len(prices)

    def test_momentum_empty_series(self):
        """Test momentum with empty series."""
        prices = pd.Series(dtype=float)
        result = calculate_momentum(prices)

        assert isinstance(result, pd.Series)
        assert len(result) == 0


class TestCalculateROC:
    """Tests for calculate_roc function."""

    @pytest.fixture
    def sample_prices(self):
        """Generate sample price data."""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 2)
        return pd.Series(prices, index=dates)

    @pytest.fixture
    def sample_numpy_prices(self):
        """Generate sample price data as numpy array."""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 2)
        return prices

    def test_roc_returns_series(self, sample_prices):
        """Test that ROC returns a pandas Series."""
        result = calculate_roc(sample_prices)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)

    def test_roc_default_period(self, sample_prices):
        """Test ROC with default period (10)."""
        result = calculate_roc(sample_prices)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)

    def test_roc_custom_period(self, sample_prices):
        """Test ROC with custom period."""
        result = calculate_roc(sample_prices, period=5)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)

    def test_roc_numpy_input(self, sample_numpy_prices):
        """Test ROC with numpy array input."""
        result = calculate_roc(sample_numpy_prices)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_numpy_prices)

    def test_roc_calculation(self):
        """Test ROC calculation is correct."""
        prices = pd.Series([100, 102, 104, 103, 105, 107, 110, 108, 110, 115])
        result = calculate_roc(prices, period=1)

        expected = ((prices - prices.shift(1)) / prices.shift(1)) * 100
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_roc_longer_period(self):
        """Test ROC with period > 1."""
        prices = pd.Series([100, 102, 104, 103, 105, 107, 109, 108, 110, 120])
        result = calculate_roc(prices, period=5)

        expected = ((prices - prices.shift(5)) / prices.shift(5)) * 100
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_roc_short_data(self):
        """Test ROC with short data."""
        prices = pd.Series([100, 101, 102])
        result = calculate_roc(prices, period=10)

        assert isinstance(result, pd.Series)
        assert len(result) == len(prices)

    def test_roc_empty_series(self):
        """Test ROC with empty series."""
        prices = pd.Series(dtype=float)
        result = calculate_roc(prices)

        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_roc_constant_prices(self):
        """Test ROC with constant prices (should be 0 after period)."""
        prices = pd.Series([100] * 20)
        result = calculate_roc(prices, period=10)

        assert isinstance(result, pd.Series)
        valid_values = result[result.notna()]
        assert len(valid_values) > 0
