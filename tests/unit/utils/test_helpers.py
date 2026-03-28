"""
Unit tests for helper utilities.

Tests cover:
- Date validation and manipulation
- Symbol normalization
- List operations
- Financial calculations
- Data formatting
- DataFrame operations
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch

from trading_system.utils.helpers import (
    validate_date_range,
    normalize_symbol,
    chunk_list,
    calculate_returns,
    resample_ohlcv,
    format_currency,
    format_percentage,
    merge_dataframes,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    align_dataframes,
)


class TestValidateDateRange:
    """Tests for validate_date_range function."""

    def test_valid_string_dates(self):
        """Test validation with string date inputs."""
        start, end = validate_date_range("2024-01-01", "2024-12-31")
        
        assert isinstance(start, pd.Timestamp)
        assert isinstance(end, pd.Timestamp)
        assert start < end

    def test_valid_datetime_objects(self):
        """Test validation with datetime objects."""
        start_dt = datetime(2024, 1, 1)
        end_dt = datetime(2024, 12, 31)
        
        start, end = validate_date_range(start_dt, end_dt)
        
        assert start == pd.Timestamp("2024-01-01")
        assert end == pd.Timestamp("2024-12-31")

    def test_valid_pandas_timestamps(self):
        """Test validation with pandas Timestamps."""
        start = pd.Timestamp("2024-06-01")
        end = pd.Timestamp("2024-06-30")
        
        result_start, result_end = validate_date_range(start, end)
        
        assert result_start == start
        assert result_end == end

    def test_same_start_and_end_date(self):
        """Test that same start and end date is valid."""
        start, end = validate_date_range("2024-01-01", "2024-01-01")
        
        assert start == end

    def test_allow_future_dates(self):
        """Test allowing future dates."""
        future_start = datetime.now() + timedelta(days=30)
        future_end = datetime.now() + timedelta(days=60)
        
        start, end = validate_date_range(future_start, future_end, allow_future=True)
        
        assert start == pd.Timestamp(future_start)
        assert end == pd.Timestamp(future_end)

    def test_future_dates_not_allowed_by_default(self):
        """Test that future dates raise error by default."""
        future_date = datetime.now() + timedelta(days=100)
        
        with pytest.raises(ValueError, match="Future dates not allowed"):
            validate_date_range("2024-01-01", future_date)

    def test_invalid_start_date_format(self):
        """Test error for invalid start date format."""
        with pytest.raises(ValueError, match="Invalid start date format"):
            validate_date_range("not-a-date", "2024-12-31")

    def test_invalid_end_date_format(self):
        """Test error for invalid end date format."""
        with pytest.raises(ValueError, match="Invalid end date format"):
            validate_date_range("2024-01-01", "invalid-date")

    def test_start_after_end_raises_error(self):
        """Test that start after end raises error."""
        with pytest.raises(ValueError, match="Start date .* must be before or equal"):
            validate_date_range("2024-12-31", "2024-01-01")

    def test_max_range_days_exceeded(self):
        """Test error when date range exceeds maximum."""
        with pytest.raises(ValueError, match="exceeds maximum allowed"):
            validate_date_range("2024-01-01", "2024-12-31", max_range_days=30)

    def test_max_range_days_exact_boundary(self):
        """Test that exact max range is allowed."""
        start, end = validate_date_range(
            "2024-01-01", 
            "2024-01-31", 
            max_range_days=30
        )
        
        assert (end - start).days == 30

    def test_invalid_date_types(self):
        """Test error for invalid date types."""
        with pytest.raises(ValueError, match="Invalid date types"):
            validate_date_range(12345, "2024-12-31")


class TestNormalizeSymbol:
    """Tests for normalize_symbol function."""

    def test_lowercase_to_uppercase(self):
        """Test converting lowercase to uppercase."""
        assert normalize_symbol("aapl") == "AAPL"
        assert normalize_symbol("googl") == "GOOGL"

    def test_mixed_case_conversion(self):
        """Test converting mixed case to uppercase."""
        assert normalize_symbol("AaPl") == "AAPL"
        assert normalize_symbol("Google") == "GOOGLE"

    def test_strips_whitespace(self):
        """Test stripping whitespace from symbols."""
        assert normalize_symbol("  AAPL  ") == "AAPL"
        assert normalize_symbol(" AAPL ") == "AAPL"

    def test_removes_exchange_prefixes(self):
        """Test removing common exchange prefixes."""
        assert normalize_symbol("NYSE:AAPL") == "AAPL"
        assert normalize_symbol("NASDAQ:MSFT") == "MSFT"
        assert normalize_symbol("AMEX:SPY") == "SPY"
        assert normalize_symbol("SP:BRK.B") == "BRK.B"

    def test_crypto_symbols(self):
        """Test handling of crypto symbols with slash."""
        assert normalize_symbol("eth/usd") == "ETH/USD"
        assert normalize_symbol("BTC/USDT") == "BTC/USDT"
        assert normalize_symbol("ETH / USD") == "ETH/USD"

    def test_class_suffix_symbols(self):
        """Test preserving class suffix symbols."""
        assert normalize_symbol("brk.b") == "BRK.B"
        assert normalize_symbol("BRK.A") == "BRK.A"
        assert normalize_symbol("BRK.B") == "BRK.B"

    def test_removes_dashes_and_spaces(self):
        """Test removing dashes and spaces."""
        assert normalize_symbol("A-A-P-L") == "AAPL"
        assert normalize_symbol("A A P L") == "AAPL"

    def test_exchange_suffix_application(self):
        """Test adding exchange suffix based on exchange parameter."""
        assert normalize_symbol("SP500", exchange="SP") == "SP500.SP"
        assert normalize_symbol("VANGUARD", exchange="V") == "VANGUARD.V"

    def test_empty_symbol_raises_error(self):
        """Test error for empty symbol."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            normalize_symbol("")

    def test_none_symbol_raises_error(self):
        """Test error for None symbol."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            normalize_symbol(None)

    def test_non_string_raises_error(self):
        """Test error for non-string symbol."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            normalize_symbol(12345)


class TestChunkList:
    """Tests for chunk_list function."""

    def test_basic_chunking(self):
        """Test basic list chunking."""
        result = list(chunk_list([1, 2, 3, 4, 5], 2))
        
        assert result == [[1, 2], [3, 4], [5]]

    def test_equal_chunks(self):
        """Test list that divides evenly."""
        result = list(chunk_list([1, 2, 3, 4], 2))
        
        assert result == [[1, 2], [3, 4]]

    def test_chunk_with_fill_value(self):
        """Test chunking with fill value for last chunk."""
        result = list(chunk_list([1, 2, 3], 2, fill_value=0))
        
        assert result == [[1, 2], [3, 0]]

    def test_empty_list(self):
        """Test chunking empty list."""
        result = list(chunk_list([], 2))
        
        assert result == []

    def test_single_element(self):
        """Test chunking single element list."""
        result = list(chunk_list([1], 2))
        
        assert result == [[1]]

    def test_chunk_size_larger_than_list(self):
        """Test when chunk size is larger than list."""
        result = list(chunk_list([1, 2], 5))
        
        assert result == [[1, 2]]

    def test_chunk_size_one(self):
        """Test chunking with size 1."""
        result = list(chunk_list([1, 2, 3], 1))
        
        assert result == [[1], [2], [3]]

    def test_zero_chunk_size_raises_error(self):
        """Test error for zero chunk size."""
        with pytest.raises(ValueError, match="Chunk size must be positive"):
            list(chunk_list([1, 2, 3], 0))

    def test_negative_chunk_size_raises_error(self):
        """Test error for negative chunk size."""
        with pytest.raises(ValueError, match="Chunk size must be positive"):
            list(chunk_list([1, 2, 3], -1))

    def test_generator_not_list_input(self):
        """Test with tuple input (demonstrates Sequence type)."""
        result = list(chunk_list((1, 2, 3, 4, 5), 2))
        
        assert result == [[1, 2], [3, 4], [5]]

    def test_preserves_original_data(self):
        """Test that chunking doesn't modify original list."""
        original = [1, 2, 3, 4, 5]
        _ = list(chunk_list(original, 2))
        
        assert original == [1, 2, 3, 4, 5]


class TestCalculateReturns:
    """Tests for calculate_returns function."""

    def test_simple_returns(self):
        """Test simple return calculation."""
        prices = pd.Series([100, 102, 101, 105])
        returns = calculate_returns(prices)
        
        assert returns.iloc[0] is pd.NA or np.isnan(returns.iloc[0])
        assert abs(returns.iloc[1] - 0.02) < 0.001
        assert abs(returns.iloc[2] - (-0.009804)) < 0.001
        assert abs(returns.iloc[3] - 0.039604) < 0.001

    def test_log_returns(self):
        """Test log return calculation."""
        prices = pd.Series([100, 102, 101, 105])
        returns = calculate_returns(prices, method="log")
        
        assert abs(returns.iloc[1] - np.log(102/100)) < 0.001

    def test_cumulative_returns(self):
        """Test cumulative return calculation."""
        prices = pd.Series([100, 110, 105, 115])
        returns = calculate_returns(prices, method="cumulative")
        
        assert abs(returns.iloc[-1] - 0.15) < 0.01

    def test_list_input(self):
        """Test with list input."""
        prices = [100, 102, 101]
        returns = calculate_returns(prices)
        
        assert isinstance(returns, pd.Series)
        assert len(returns) == 3

    def test_numpy_array_input(self):
        """Test with numpy array input."""
        prices = np.array([100, 102, 101, 105])
        returns = calculate_returns(prices)
        
        assert isinstance(returns, pd.Series)

    def test_invalid_method_raises_error(self):
        """Test error for invalid method."""
        with pytest.raises(ValueError, match="Unknown method"):
            calculate_returns([100, 102], method="invalid")

    def test_invalid_price_type_raises_error(self):
        """Test error for invalid price type."""
        with pytest.raises(TypeError, match="prices must be a Series"):
            calculate_returns("invalid")

    def test_periods_parameter(self):
        """Test calculation with different periods."""
        prices = pd.Series([100, 105, 110, 115, 120])
        returns = calculate_returns(prices, periods=2)
        
        assert abs(returns.iloc[2] - 0.10) < 0.001

    def test_empty_series(self):
        """Test with empty series."""
        prices = pd.Series([], dtype=float)
        returns = calculate_returns(prices)
        
        assert len(returns) == 0

    def test_single_value(self):
        """Test with single value."""
        prices = pd.Series([100])
        returns = calculate_returns(prices)
        
        assert len(returns) == 1


class TestResampleOhlcv:
    """Tests for resample_ohlcv function."""

    @pytest.fixture
    def sample_ohlcv_df(self):
        """Create sample OHLCV DataFrame."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="h")
        np.random.seed(42)
        base = 100 + np.cumsum(np.random.randn(100) * 0.5)
        
        return pd.DataFrame({
            "Open": base + 0.5,
            "High": base + 2,
            "Low": base - 2,
            "Close": base,
            "Volume": np.random.randint(1000, 5000, 100)
        }, index=dates)

    def test_resample_to_daily(self, sample_ohlcv_df):
        """Test resampling hourly to daily."""
        daily = resample_ohlcv(sample_ohlcv_df, "1D")
        
        assert len(daily) < len(sample_ohlcv_df)
        assert "Open" in daily.columns or "open" in daily.columns
        assert "High" in daily.columns or "high" in daily.columns
        assert "Low" in daily.columns or "low" in daily.columns
        assert "Close" in daily.columns or "close" in daily.columns
        assert "Volume" in daily.columns or "volume" in daily.columns

    def test_resample_to_hourly(self, sample_ohlcv_df):
        """Test resampling to larger timeframe."""
        result = resample_ohlcv(sample_ohlcv_df, "12h")
        
        assert len(result) < len(sample_ohlcv_df)
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_missing_columns_raises_error(self):
        """Test error for missing required columns."""
        df = pd.DataFrame({"open": [1, 2, 3], "close": [1, 2, 3]})
        df.index = pd.date_range("2024-01-01", periods=3)
        
        with pytest.raises(ValueError, match="Missing required columns"):
            resample_ohlcv(df, "1D")

    def test_non_datetime_index_raises_error(self):
        """Test error for non-DatetimeIndex."""
        df = pd.DataFrame({
            "open": [1, 2, 3],
            "high": [2, 3, 4],
            "low": [0, 1, 2],
            "close": [1, 2, 3],
            "volume": [100, 200, 300]
        })
        
        with pytest.raises(ValueError, match="DatetimeIndex"):
            resample_ohlcv(df, "1D")

    def test_custom_aggregation_config(self, sample_ohlcv_df):
        """Test with custom aggregation configuration."""
        custom_config = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }
        
        result = resample_ohlcv(sample_ohlcv_df, "12h", agg_config=custom_config)
        
        assert len(result) > 0

    def test_drops_all_nan_rows(self, sample_ohlcv_df):
        """Test that rows with all NaN are dropped."""
        result = resample_ohlcv(sample_ohlcv_df, "1d")
        
        assert not result.isna().all(axis=1).any()


class TestFormatCurrency:
    """Tests for format_currency function."""

    def test_usd_default(self):
        """Test default USD formatting."""
        result = format_currency(1234.56)
        
        assert result == "$1,234.56"

    def test_different_currencies(self):
        """Test formatting different currencies."""
        assert format_currency(1000, currency="EUR") == "€1,000.00"
        assert format_currency(1000, currency="GBP") == "£1,000.00"
        assert format_currency(1000, currency="JPY") == "¥1,000.00"

    def test_negative_value(self):
        """Test formatting negative values."""
        result = format_currency(-500)
        
        assert result == "-$500.00"

    def test_positive_with_sign(self):
        """Test including positive sign."""
        result = format_currency(500, include_sign=True)
        
        assert result == "+$500.00"

    def test_without_symbol(self):
        """Test formatting without currency symbol."""
        result = format_currency(1234.56, include_symbol=False)
        
        assert result == "1,234.56"

    def test_different_decimals(self):
        """Test different decimal places."""
        assert format_currency(1234.5, decimals=0) == "$1,234"
        assert format_currency(1234.567, decimals=3) == "$1,234.567"

    def test_large_numbers(self):
        """Test formatting large numbers."""
        assert format_currency(1000000) == "$1,000,000.00"
        assert format_currency(1000000000) == "$1,000,000,000.00"

    def test_small_numbers(self):
        """Test formatting small numbers."""
        result = format_currency(0.01)
        
        assert result == "$0.01"

    def test_zero_value(self):
        """Test formatting zero."""
        result = format_currency(0)
        
        assert result == "$0.00"

    def test_unknown_currency(self):
        """Test with unknown currency code."""
        result = format_currency(100, currency="XYZ")
        
        assert "XYZ" in result

    def test_negative_with_sign_flag(self):
        """Test that negative values ignore positive sign flag."""
        result = format_currency(-100, include_sign=True)
        
        assert result == "-$100.00"


class TestFormatPercentage:
    """Tests for format_percentage function."""

    def test_decimal_format(self):
        """Test formatting decimal values (0.05 = 5%)."""
        result = format_percentage(0.05)
        
        assert result == "+5.00%"

    def test_direct_percentage_format(self):
        """Test formatting values already in percentage form."""
        result = format_percentage(5)
        
        assert result == "+500.00%"

    def test_negative_percentage(self):
        """Test formatting negative percentages."""
        result = format_percentage(-0.15)
        
        assert result == "-15.00%"

    def test_positive_with_sign(self):
        """Test including positive sign for positive values."""
        result = format_percentage(0.05, include_sign=True)
        
        assert result == "+5.00%"

    def test_without_symbol(self):
        """Test formatting without percentage symbol."""
        result = format_percentage(0.05, include_symbol=False)
        
        assert result == "+5.00"

    def test_different_decimals(self):
        """Test different decimal places."""
        assert format_percentage(5.123, decimals=1) == "+512.3%"
        assert format_percentage(5.12345, decimals=4) == "+512.3450%"

    def test_zero_value(self):
        """Test formatting zero."""
        result = format_percentage(0)
        
        assert result == "0.00%"

    def test_large_percentage(self):
        """Test formatting large percentages."""
        result = format_percentage(150)
        
        assert result == "+150.00%"

    def test_small_percentage(self):
        """Test formatting very small percentages."""
        result = format_percentage(0.001)
        
        assert result == "+0.10%"

    def test_negative_with_sign_flag(self):
        """Test that negative values ignore positive sign flag."""
        result = format_percentage(-0.50, include_sign=True)
        
        assert result == "-50.00%"


class TestMergeDataframes:
    """Tests for merge_dataframes function."""

    @pytest.fixture
    def sample_dfs(self):
        """Create sample DataFrames for merging."""
        df1 = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "price": [100, 102, 101, 105, 103]
        })
        df2 = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "volume": [1000, 1500, 1200, 1800, 1100]
        })
        df3 = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "open": [99, 101, 100, 104, 102]
        })
        return df1, df2, df3

    def test_merge_two_dataframes(self, sample_dfs):
        """Test merging two DataFrames."""
        df1, df2, _ = sample_dfs
        
        result = merge_dataframes([df1, df2], on="date")
        
        assert len(result) == 5
        assert "price" in result.columns
        assert "volume" in result.columns

    def test_merge_three_dataframes(self, sample_dfs):
        """Test merging three DataFrames."""
        df1, df2, df3 = sample_dfs
        
        result = merge_dataframes([df1, df2, df3], on="date")
        
        assert len(result) == 5
        assert "price" in result.columns
        assert "volume" in result.columns
        assert "open" in result.columns

    def test_different_merge_types(self, sample_dfs):
        """Test different merge types."""
        df1, df2, _ = sample_dfs
        
        result_inner = merge_dataframes([df1, df2], on="date", how="inner")
        result_left = merge_dataframes([df1, df2], on="date", how="left")
        
        assert len(result_inner) == 5
        assert len(result_left) == 5

    def test_less_than_two_dataframes_raises_error(self):
        """Test error for less than 2 DataFrames."""
        with pytest.raises(ValueError, match="At least 2 DataFrames required"):
            merge_dataframes([])

    def test_single_dataframe_raises_error(self):
        """Test error for single DataFrame."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        
        with pytest.raises(ValueError, match="At least 2 DataFrames required"):
            merge_dataframes([df])


class TestCalculateSharpeRatio:
    """Tests for calculate_sharpe_ratio function."""

    def test_basic_sharpe_ratio(self):
        """Test basic Sharpe ratio calculation."""
        returns = pd.Series([0.01, -0.005, 0.02, 0.015, -0.01])
        
        sharpe = calculate_sharpe_ratio(returns)
        
        assert isinstance(sharpe, float)
        assert not np.isnan(sharpe)

    def test_list_input(self):
        """Test with list input."""
        returns = [0.01, -0.005, 0.02, 0.015]
        
        sharpe = calculate_sharpe_ratio(returns)
        
        assert isinstance(sharpe, float)

    def test_zero_std_returns_zero(self):
        """Test that zero std returns 0."""
        returns = pd.Series([0.01, 0.01, 0.01, 0.01])
        
        sharpe = calculate_sharpe_ratio(returns)
        
        assert sharpe == 0.0

    def test_with_risk_free_rate(self):
        """Test Sharpe ratio with risk-free rate."""
        returns = pd.Series([0.01, -0.005, 0.02, 0.015])
        
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        
        assert isinstance(sharpe, float)


class TestCalculateMaxDrawdown:
    """Tests for calculate_max_drawdown function."""

    def test_basic_drawdown(self):
        """Test basic max drawdown calculation."""
        equity = pd.Series([100, 110, 105, 95, 100, 120])
        
        max_dd, peak_idx, trough_idx = calculate_max_drawdown(equity)
        
        assert isinstance(max_dd, float)
        assert max_dd < 0  # Drawdown should be negative
        assert peak_idx < trough_idx

    def test_list_input(self):
        """Test with list input."""
        equity = [100, 110, 105, 95, 100]
        
        max_dd, peak_idx, trough_idx = calculate_max_drawdown(equity)
        
        assert isinstance(max_dd, float)

    def test_no_drawdown(self):
        """Test with continuously rising equity."""
        equity = pd.Series([100, 110, 120, 130, 140])
        
        max_dd, _, _ = calculate_max_drawdown(equity)
        
        assert max_dd == 0.0

    def test_drawdown_at_end(self):
        """Test drawdown when peak is early."""
        equity = pd.Series([100, 120, 110, 90, 80])
        
        max_dd, peak_idx, trough_idx = calculate_max_drawdown(equity)
        
        assert peak_idx == 1  # Peak at 120
        assert trough_idx > peak_idx

    def test_empty_series(self):
        """Test with empty series."""
        equity = pd.Series([], dtype=float)
        
        with pytest.raises(Exception):
            calculate_max_drawdown(equity)


class TestAlignDataframes:
    """Tests for align_dataframes function."""

    @pytest.fixture
    def misaligned_dfs(self):
        """Create misaligned DataFrames."""
        dates1 = pd.date_range("2024-01-01", periods=5)
        dates2 = pd.date_range("2024-01-02", periods=4)
        dates3 = pd.date_range("2024-01-03", periods=3)
        
        df1 = pd.DataFrame({"value": [1, 2, 3, 4, 5]}, index=dates1)
        df2 = pd.DataFrame({"value": [10, 20, 30, 40]}, index=dates2)
        df3 = pd.DataFrame({"value": [100, 200, 300]}, index=dates3)
        
        return df1, df2, df3

    def test_inner_align(self, misaligned_dfs):
        """Test inner alignment (common index)."""
        df1, df2, df3 = misaligned_dfs
        
        aligned = align_dataframes(df1, df2, df3, how="inner")
        
        assert len(aligned) == 3
        assert all(len(d) == len(aligned[0]) for d in aligned)

    def test_outer_align(self, misaligned_dfs):
        """Test outer alignment (all indices)."""
        df1, df2, df3 = misaligned_dfs
        
        aligned = align_dataframes(df1, df2, df3, how="outer")
        
        assert len(aligned) == 3
        # Outer should have more rows than inner
        assert len(aligned[0]) >= 3

    def test_empty_input(self):
        """Test with empty input."""
        result = align_dataframes()
        
        assert result == []

    def test_single_dataframe(self):
        """Test with single DataFrame."""
        df = pd.DataFrame(
            {"value": [1, 2, 3]},
            index=pd.date_range("2024-01-01", periods=3)
        )
        
        aligned = align_dataframes(df)
        
        assert len(aligned) == 1
        assert len(aligned[0]) == 3
