"""
Data validators module.

Provides validation and quality checking for OHLCV data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from trading_system.exceptions import DataValidationError


@dataclass
class DataQualityReport:
    """
    Report containing data quality metrics.

    Attributes:
        missing_rows: Number of rows with missing values
        duplicates: Number of duplicate timestamps
        outliers: Number of detected price/volume outliers
        price_anomalies: Number of OHLC consistency violations
        volume_anomalies: Number of invalid volume entries
        quality_score: Overall quality score (0-100)
        issues: List of specific issues found
    """

    missing_rows: int = 0
    duplicates: int = 0
    outliers: int = 0
    price_anomalies: int = 0
    volume_anomalies: int = 0
    quality_score: float = 100.0
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "missing_rows": self.missing_rows,
            "duplicates": self.duplicates,
            "outliers": self.outliers,
            "price_anomalies": self.price_anomalies,
            "volume_anomalies": self.volume_anomalies,
            "quality_score": self.quality_score,
            "issues": self.issues
        }

    @property
    def is_acceptable(self) -> bool:
        """Check if quality score is above acceptable threshold (70)."""
        return self.quality_score >= 70.0


class DataValidator:
    """
    Validator for OHLCV data quality and integrity.

    Provides comprehensive validation including:
    - OHLCV structure validation
    - Symbol format validation
    - Date range validation
    - Data quality assessment

    Example:
        >>> validator = DataValidator()
        >>> validator.validate_ohlcv(data)
        >>> report = validator.check_data_quality(data)
        >>> print(f"Quality: {report.quality_score}")
    """

    REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]
    MAX_OUTLIER_STD = 5.0
    MIN_VOLUME = 0
    MAX_VOLUME_RATIO = 100.0

    def __init__(
        self,
        min_data_points: int = 2,
        quality_threshold: float = 70.0
    ):
        """
        Initialize validator.

        Args:
            min_data_points: Minimum required data points
            quality_threshold: Minimum acceptable quality score
        """
        self.min_data_points = min_data_points
        self.quality_threshold = quality_threshold

    def validate_ohlcv(self, data: pd.DataFrame) -> None:
        """
        Validate OHLCV DataFrame structure and values.

        Args:
            data: DataFrame with OHLCV data

        Raises:
            DataValidationError: If validation fails
        """
        errors: List[str] = []

        if data is None or data.empty:
            errors.append("Data is empty")
            raise DataValidationError(errors)

        missing_cols = set(self.REQUIRED_COLUMNS) - set(data.columns)
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")

        if len(data) < self.min_data_points:
            errors.append(
                f"Insufficient data points: {len(data)} < {self.min_data_points}"
            )

        for col in self.REQUIRED_COLUMNS:
            if col in data.columns:
                if data[col].isna().any():
                    na_count = data[col].isna().sum()
                    errors.append(f"Column '{col}' has {na_count} missing values")

        if "high" in data.columns and "low" in data.columns:
            invalid_hl = (data["high"] < data["low"]).sum()
            if invalid_hl > 0:
                errors.append(f"Found {invalid_hl} rows where high < low")

        if all(col in data.columns for col in ["open", "high", "low", "close"]):
            invalid_ohlc = (
                (data["high"] < data["open"]) |
                (data["high"] < data["close"]) |
                (data["low"] > data["open"]) |
                (data["low"] > data["close"])
            ).sum()
            if invalid_ohlc > 0:
                errors.append(f"Found {invalid_ohlc} rows with OHLC violations")

        if errors:
            raise DataValidationError(errors)

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate ticker symbol format.

        Args:
            symbol: Stock symbol to validate

        Returns:
            True if valid

        Raises:
            DataValidationError: If symbol is invalid
        """
        if not symbol:
            raise DataValidationError(["Symbol cannot be empty"])

        symbol = symbol.strip().upper()

        if len(symbol) < 1 or len(symbol) > 10:
            raise DataValidationError(
                [f"Invalid symbol length: {len(symbol)} (expected 1-10)"]
            )

        if not symbol.replace("-", "").replace(".", "").isalnum():
            raise DataValidationError(
                [f"Invalid symbol format: '{symbol}' (alphanumeric only)"]
            )

        return True

    def validate_date_range(
        self,
        start: str,
        end: str,
        max_days: Optional[int] = None
    ) -> Tuple[datetime, datetime]:
        """
        Validate and parse date range.

        Args:
            start: Start date string (YYYY-MM-DD)
            end: End date string (YYYY-MM-DD)
            max_days: Optional maximum days allowed

        Returns:
            Tuple of (start_datetime, end_datetime)

        Raises:
            DataValidationError: If dates are invalid
        """
        errors: List[str] = []

        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
        except ValueError:
            errors.append(f"Invalid start date format: '{start}' (use YYYY-MM-DD)")

        try:
            end_dt = datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            errors.append(f"Invalid end date format: '{end}' (use YYYY-MM-DD)")

        if not errors:
            if start_dt > end_dt:
                errors.append("Start date must be before end date")

            if start_dt == end_dt:
                errors.append("Start and end dates cannot be the same")

            if max_days is not None:
                days_diff = (end_dt - start_dt).days
                if days_diff > max_days:
                    errors.append(
                        f"Date range exceeds maximum: {days_diff} > {max_days} days"
                    )

        if errors:
            raise DataValidationError(errors)

        return start_dt, end_dt

    def check_data_quality(self, data: pd.DataFrame) -> DataQualityReport:
        """
        Perform comprehensive data quality check.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataQualityReport with quality metrics
        """
        report = DataQualityReport()

        if data is None or data.empty:
            report.quality_score = 0.0
            report.issues.append("Empty dataset")
            return report

        report.missing_rows = int(data.isna().any(axis=1).sum())

        if isinstance(data.index, pd.DatetimeIndex):
            duplicates = data.index.duplicated().sum()
            report.duplicates = int(duplicates)
            if duplicates > 0:
                report.issues.append(f"Found {duplicates} duplicate timestamps")

        price_cols = ["open", "high", "low", "close"]
        if all(col in data.columns for col in price_cols):
            invalid_hl = (data["high"] < data["low"]).sum()
            report.price_anomalies = int(invalid_hl)

            invalid_bounds = (
                (data["high"] < data["open"]) |
                (data["high"] < data["close"]) |
                (data["low"] > data["open"]) |
                (data["low"] > data["close"])
            ).sum()
            report.price_anomalies += int(invalid_bounds)

        if "volume" in data.columns:
            zero_volume = (data["volume"] <= self.MIN_VOLUME).sum()
            report.volume_anomalies = int(zero_volume)

        report.outliers = self._detect_outliers(data)

        report.quality_score = self._calculate_quality_score(report, len(data))

        return report

    def _detect_outliers(self, data: pd.DataFrame) -> int:
        """
        Detect price and volume outliers using z-score.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Number of detected outliers
        """
        outlier_count = 0

        price_cols = ["open", "high", "low", "close"]
        for col in price_cols:
            if col in data.columns:
                outliers = self._find_outliers_zscore(data[col])
                outlier_count += outliers

        if "volume" in data.columns:
            volume_outliers = self._find_outliers_zscore(data["volume"])
            outlier_count += volume_outliers

        return outlier_count

    def _find_outliers_zscore(self, series: pd.Series, threshold: float = 5.0) -> int:
        """
        Find outliers using z-score method.

        Args:
            series: Data series to check
            threshold: Z-score threshold

        Returns:
            Number of outliers
        """
        if len(series) < 3:
            return 0

        mean = series.mean()
        std = series.std()

        if std == 0:
            return 0

        z_scores = ((series - mean) / std).abs()
        return int((z_scores > threshold).sum())

    def _calculate_quality_score(
        self,
        report: DataQualityReport,
        total_rows: int
    ) -> float:
        """
        Calculate overall quality score (0-100).

        Score deductions:
        - Missing rows: -5 per row (max -50)
        - Duplicates: -10 per duplicate (max -30)
        - Price anomalies: -5 per anomaly (max -40)
        - Volume anomalies: -2 per anomaly (max -20)
        - Outliers: -1 per outlier (max -20)
        """
        if total_rows == 0:
            return 0.0

        score = 100.0

        missing_penalty = min(report.missing_rows * 5, 50)
        score -= missing_penalty

        dup_penalty = min(report.duplicates * 10, 30)
        score -= dup_penalty

        price_penalty = min(report.price_anomalies * 5, 40)
        score -= price_penalty

        volume_penalty = min(report.volume_anomalies * 2, 20)
        score -= volume_penalty

        outlier_penalty = min(report.outliers * 1, 20)
        score -= outlier_penalty

        return max(0.0, min(100.0, score))

    def validate_batch(
        self,
        data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, DataQualityReport]:
        """
        Validate multiple datasets.

        Args:
            data_dict: Dictionary mapping symbols to DataFrames

        Returns:
            Dictionary mapping symbols to quality reports
        """
        reports = {}

        for symbol, data in data_dict.items():
            try:
                self.validate_ohlcv(data)
                reports[symbol] = self.check_data_quality(data)
            except DataValidationError as e:
                report = DataQualityReport()
                report.quality_score = 0.0
                report.issues = e.errors
                reports[symbol] = report

        return reports
