"""
Unit tests for data validator.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from trading_system.data.validators import DataValidator, DataQualityReport
from trading_system.exceptions import DataValidationError


class TestDataQualityReport:
    """Tests for DataQualityReport dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        report = DataQualityReport()
        
        assert report.missing_rows == 0
        assert report.duplicates == 0
        assert report.outliers == 0
        assert report.price_anomalies == 0
        assert report.volume_anomalies == 0
        assert report.quality_score == 100.0
        assert report.issues == []

    def test_to_dict(self):
        """Test conversion to dictionary."""
        report = DataQualityReport(
            missing_rows=2,
            duplicates=1,
            outliers=3,
            quality_score=85.0,
            issues=["Issue 1", "Issue 2"]
        )
        
        result = report.to_dict()
        
        assert result["missing_rows"] == 2
        assert result["duplicates"] == 1
        assert result["outliers"] == 3
        assert result["quality_score"] == 85.0
        assert len(result["issues"]) == 2

    def test_is_acceptable_above_threshold(self):
        """Test is_acceptable returns True when above threshold."""
        report = DataQualityReport(quality_score=75.0)
        assert report.is_acceptable is True

    def test_is_acceptable_at_threshold(self):
        """Test is_acceptable returns True at exact threshold."""
        report = DataQualityReport(quality_score=70.0)
        assert report.is_acceptable is True

    def test_is_acceptable_below_threshold(self):
        """Test is_acceptable returns False when below threshold."""
        report = DataQualityReport(quality_score=69.0)
        assert report.is_acceptable is False

    def test_is_acceptable_at_zero(self):
        """Test is_acceptable with zero score."""
        report = DataQualityReport(quality_score=0.0)
        assert report.is_acceptable is False

    def test_is_acceptable_at_max(self):
        """Test is_acceptable with max score."""
        report = DataQualityReport(quality_score=100.0)
        assert report.is_acceptable is True


class TestDataValidator:
    """Tests for DataValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance for testing."""
        return DataValidator()

    @pytest.fixture
    def valid_ohlcv_data(self):
        """Create valid OHLCV data."""
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        return pd.DataFrame({
            "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
            "high": [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
            "close": [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
            "volume": [1000000, 1100000, 1200000, 1300000, 1400000, 1500000, 1600000, 1700000, 1800000, 1900000]
        }, index=dates)

    @pytest.fixture
    def empty_data(self):
        """Create empty DataFrame."""
        return pd.DataFrame()

    @pytest.fixture
    def data_with_missing_columns(self):
        """Create data with missing required columns."""
        return pd.DataFrame({
            "open": [100.0],
            "close": [101.0]
        })

    @pytest.fixture
    def data_with_missing_values(self):
        """Create data with missing values."""
        dates = pd.date_range("2023-01-01", periods=5, freq="D")
        return pd.DataFrame({
            "open": [100.0, np.nan, 102.0, 103.0, 104.0],
            "high": [102.0, 103.0, 104.0, 105.0, 106.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [101.0, 102.0, np.nan, 104.0, 105.0],
            "volume": [1000000, 1100000, 1200000, 1300000, 1400000]
        }, index=dates)

    @pytest.fixture
    def data_with_hl_violations(self):
        """Create data with high < low violations."""
        dates = pd.date_range("2023-01-01", periods=3, freq="D")
        return pd.DataFrame({
            "open": [100.0, 105.0, 102.0],
            "high": [98.0, 103.0, 106.0],  # First two have high < low
            "low": [99.0, 104.0, 101.0],
            "close": [99.0, 104.0, 105.0],
            "volume": [1000000, 1100000, 1200000]
        }, index=dates)

    @pytest.fixture
    def data_with_ohlc_violations(self):
        """Create data with OHLC consistency violations."""
        dates = pd.date_range("2023-01-01", periods=3, freq="D")
        return pd.DataFrame({
            "open": [105.0, 100.0, 100.0],  # open > high
            "high": [100.0, 102.0, 102.0],
            "low": [95.0, 98.0, 98.0],
            "close": [100.0, 101.0, 103.0],  # close > high
            "volume": [1000000, 1100000, 1200000]
        }, index=dates)

    # === validate_ohlcv tests ===

    def test_validate_ohlcv_valid_data(self, validator, valid_ohlcv_data):
        """Test validation passes with valid data."""
        # Should not raise
        validator.validate_ohlcv(valid_ohlcv_data)

    def test_validate_ohlcv_empty_dataframe(self, validator, empty_data):
        """Test validation fails with empty DataFrame."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_ohlcv(empty_data)
        
        assert "empty" in str(exc_info.value).lower()

    def test_validate_ohlcv_none_data(self, validator):
        """Test validation fails with None data."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_ohlcv(None)
        
        assert "empty" in str(exc_info.value).lower()

    def test_validate_ohlcv_missing_columns(self, validator, data_with_missing_columns):
        """Test validation fails with missing columns."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_ohlcv(data_with_missing_columns)
        
        errors = exc_info.value.errors
        assert any("Missing required columns" in str(e) for e in errors)

    def test_validate_ohlcv_insufficient_data_points(self, validator):
        """Test validation fails with insufficient data points."""
        dates = pd.date_range("2023-01-01", periods=1, freq="D")
        data = pd.DataFrame({
            "open": [100.0],
            "high": [102.0],
            "low": [99.0],
            "close": [101.0],
            "volume": [1000000]
        }, index=dates)
        
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_ohlcv(data)
        
        errors = exc_info.value.errors
        assert any("Insufficient data points" in str(e) for e in errors)

    def test_validate_ohlcv_missing_values(self, validator, data_with_missing_values):
        """Test validation fails with missing values."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_ohlcv(data_with_missing_values)
        
        errors = exc_info.value.errors
        assert any("missing values" in str(e).lower() for e in errors)

    def test_validate_ohlcv_high_less_than_low(self, validator, data_with_hl_violations):
        """Test validation fails when high < low."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_ohlcv(data_with_hl_violations)
        
        errors = exc_info.value.errors
        assert any("high < low" in str(e).lower() for e in errors)

    def test_validate_ohlcv_ohlc_violations(self, validator, data_with_ohlc_violations):
        """Test validation fails with OHLC consistency violations."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_ohlcv(data_with_ohlc_violations)
        
        errors = exc_info.value.errors
        assert any("OHLC violations" in str(e) for e in errors)

    # === validate_symbol tests ===

    def test_validate_symbol_valid(self, validator):
        """Test validation passes with valid symbols."""
        valid_symbols = ["AAPL", "GOOGL", "MSFT", "a", "BRK.A", "BF-B", "12345"]
        for symbol in valid_symbols:
            assert validator.validate_symbol(symbol) is True

    def test_validate_symbol_empty(self, validator):
        """Test validation fails with empty symbol."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_symbol("")
        
        assert "empty" in str(exc_info.value).lower()

    def test_validate_symbol_none(self, validator):
        """Test validation fails with None symbol."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_symbol(None)
        
        assert "empty" in str(exc_info.value).lower()

    def test_validate_symbol_too_long(self, validator):
        """Test validation fails with symbol exceeding max length."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_symbol("ABCDEFGHIJK")  # 11 chars
        
        assert "length" in str(exc_info.value).lower()

    def test_validate_symbol_invalid_characters(self, validator):
        """Test validation fails with invalid characters."""
        invalid_symbols = ["AAPL!", "GO@OGL", "MS#FT", "A B C"]
        for symbol in invalid_symbols:
            with pytest.raises(DataValidationError):
                validator.validate_symbol(symbol)

    def test_validate_symbol_strips_whitespace(self, validator):
        """Test validation strips whitespace from symbol."""
        assert validator.validate_symbol("  AAPL  ") is True

    def test_validate_symbol_uppercases(self, validator):
        """Test validation converts symbol to uppercase."""
        assert validator.validate_symbol("aapl") is True

    # === validate_date_range tests ===

    def test_validate_date_range_valid(self, validator):
        """Test validation passes with valid date range."""
        start, end = validator.validate_date_range("2023-01-01", "2023-12-31")
        
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        assert start < end

    def test_validate_date_range_with_max_days(self, validator):
        """Test validation with max_days parameter."""
        start, end = validator.validate_date_range(
            "2023-01-01", "2023-01-10", max_days=10
        )
        
        assert (end - start).days == 9

    def test_validate_date_range_invalid_start_format(self, validator):
        """Test validation fails with invalid start date format."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_date_range("01-01-2023", "2023-12-31")
        
        assert "start date format" in str(exc_info.value).lower()

    def test_validate_date_range_invalid_end_format(self, validator):
        """Test validation fails with invalid end date format."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_date_range("2023-01-01", "12/31/2023")
        
        assert "end date format" in str(exc_info.value).lower()

    def test_validate_date_range_start_after_end(self, validator):
        """Test validation fails when start is after end."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_date_range("2023-12-31", "2023-01-01")
        
        assert "before" in str(exc_info.value).lower()

    def test_validate_date_range_same_date(self, validator):
        """Test validation fails when start equals end."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_date_range("2023-01-01", "2023-01-01")
        
        assert "same" in str(exc_info.value).lower()

    def test_validate_date_range_exceeds_max_days(self, validator):
        """Test validation fails when range exceeds max_days."""
        with pytest.raises(DataValidationError) as exc_info:
            validator.validate_date_range("2023-01-01", "2023-06-01", max_days=30)
        
        assert "exceeds" in str(exc_info.value).lower() or "maximum" in str(exc_info.value).lower()

    def test_validate_date_range_edge_case_max_days(self, validator):
        """Test validation passes when range equals max_days."""
        start, end = validator.validate_date_range(
            "2023-01-01", "2023-01-31", max_days=30
        )
        assert (end - start).days == 30

    # === check_data_quality tests ===

    def test_check_data_quality_valid_data(self, validator, valid_ohlcv_data):
        """Test quality check with valid data returns high score."""
        report = validator.check_data_quality(valid_ohlcv_data)
        
        assert report.quality_score >= 90.0
        assert len(report.issues) == 0

    def test_check_data_quality_empty_data(self, validator, empty_data):
        """Test quality check with empty data returns zero score."""
        report = validator.check_data_quality(empty_data)
        
        assert report.quality_score == 0.0
        assert "Empty" in report.issues[0]

    def test_check_data_quality_none_data(self, validator):
        """Test quality check with None data returns zero score."""
        report = validator.check_data_quality(None)
        
        assert report.quality_score == 0.0
        assert "Empty" in report.issues[0]

    def test_check_data_quality_missing_rows(self, validator, data_with_missing_values):
        """Test quality check detects missing rows."""
        report = validator.check_data_quality(data_with_missing_values)
        
        assert report.missing_rows == 2  # Two rows with NaN

    def test_check_data_quality_duplicates(self, validator):
        """Test quality check detects duplicate timestamps."""
        dates = pd.date_range("2023-01-01", periods=5, freq="D")
        # Insert duplicate index
        data = pd.DataFrame({
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [102.0, 103.0, 104.0, 105.0, 106.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [101.0, 102.0, 103.0, 104.0, 105.0],
            "volume": [1000000, 1100000, 1200000, 1300000, 1400000]
        }, index=dates)
        
        # Add duplicate index
        data.loc[dates[2]] = [102.0, 104.0, 101.0, 103.0, 1200000]
        
        report = validator.check_data_quality(data)
        
        assert report.duplicates >= 1

    def test_check_data_quality_price_anomalies(self, validator, data_with_hl_violations):
        """Test quality check detects price anomalies."""
        report = validator.check_data_quality(data_with_hl_violations)
        
        assert report.price_anomalies >= 2

    def test_check_data_quality_zero_volume(self, validator):
        """Test quality check detects zero volume entries."""
        dates = pd.date_range("2023-01-01", periods=5, freq="D")
        data = pd.DataFrame({
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [102.0, 103.0, 104.0, 105.0, 106.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [101.0, 102.0, 103.0, 104.0, 105.0],
            "volume": [1000000, 0, 1200000, 0, 1400000]  # Two zero volumes
        }, index=dates)
        
        report = validator.check_data_quality(data)
        
        assert report.volume_anomalies == 2

    def test_check_data_quality_outliers(self, validator):
        """Test quality check detects outliers."""
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        np.random.seed(42)
        
        # Normal data with some extreme outliers
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        prices[50] = 500  # Extreme outlier
        
        data = pd.DataFrame({
            "open": prices + np.random.randn(100) * 0.5,
            "high": prices + abs(np.random.randn(100)) * 2,
            "low": prices - abs(np.random.randn(100)) * 2,
            "close": prices,
            "volume": np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        report = validator.check_data_quality(data)
        
        assert report.outliers >= 1

    def test_check_data_quality_score_calculation(self, validator):
        """Test that quality score is calculated correctly."""
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        data = pd.DataFrame({
            "open": [100.0] * 10,
            "high": [102.0] * 10,
            "low": [99.0] * 10,
            "close": [101.0] * 10,
            "volume": [1000000] * 10
        }, index=dates)
        
        report = validator.check_data_quality(data)
        
        # Perfect data should have score of 100
        assert report.quality_score == 100.0

    # === _detect_outliers tests ===

    def test_detect_outliers_insufficient_data(self, validator):
        """Test outlier detection with insufficient data points."""
        dates = pd.date_range("2023-01-01", periods=2, freq="D")
        data = pd.DataFrame({
            "open": [100.0, 200.0],
            "high": [102.0, 202.0],
            "low": [99.0, 199.0],
            "close": [101.0, 201.0],
            "volume": [1000000, 2000000]
        }, index=dates)
        
        outliers = validator._detect_outliers(data)
        
        # Less than 3 points should return 0
        assert outliers == 0

    def test_detect_outliers_no_outliers(self, validator):
        """Test outlier detection with no outliers."""
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        data = pd.DataFrame({
            "open": [100.0 + i for i in range(10)],
            "high": [102.0 + i for i in range(10)],
            "low": [99.0 + i for i in range(10)],
            "close": [101.0 + i for i in range(10)],
            "volume": [1000000 + i * 10000 for i in range(10)]
        }, index=dates)
        
        outliers = validator._detect_outliers(data)
        
        assert outliers == 0

    # === validate_batch tests ===

    def test_validate_batch_multiple_symbols(self, validator, valid_ohlcv_data):
        """Test batch validation of multiple symbols."""
        data_dict = {
            "AAPL": valid_ohlcv_data.copy(),
            "GOOGL": valid_ohlcv_data.copy()
        }
        
        reports = validator.validate_batch(data_dict)
        
        assert "AAPL" in reports
        assert "GOOGL" in reports
        assert all(r.quality_score > 0 for r in reports.values())

    def test_validate_batch_with_invalid_data(self, validator, valid_ohlcv_data, empty_data):
        """Test batch validation with some invalid data."""
        data_dict = {
            "AAPL": valid_ohlcv_data.copy(),
            "GOOGL": empty_data
        }
        
        reports = validator.validate_batch(data_dict)
        
        assert reports["AAPL"].quality_score > reports["GOOGL"].quality_score

    def test_validate_batch_empty_dict(self, validator):
        """Test batch validation with empty dictionary."""
        reports = validator.validate_batch({})
        
        assert len(reports) == 0
