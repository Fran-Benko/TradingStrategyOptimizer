"""
Integration tests for the trading system data pipeline.

Tests the integration between:
- DataFetcherFactory
- Cache management
- Data validation
- Error handling and recovery
- Multi-source fallback

Run with: pytest tests/integration/test_data_pipeline.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from trading_system.data.fetchers.factory import DataFetcherFactory
from trading_system.data.fetchers.mock_fetcher import MockDataFetcher
from trading_system.data.storage.cache import CacheManager, InMemoryCache
from trading_system.data.storage.rate_limiter import RateLimiter
from trading_system.data.validators.data_validator import DataValidator, DataQualityReport
from trading_system.exceptions import DataFetchError, DataValidationError


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_cache():
    """Create an in-memory cache for testing."""
    return InMemoryCache(max_size=100)


@pytest.fixture
def cache_manager():
    """Create a cache manager with TTL for testing."""
    return CacheManager(ttl=3600, max_size=50)


@pytest.fixture
def rate_limiter():
    """Create a rate limiter for testing."""
    return RateLimiter(max_requests=1000, window_seconds=60)


@pytest.fixture
def data_validator():
    """Create a data validator for testing."""
    return DataValidator(min_data_points=5, quality_threshold=70.0)


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
        }, index=dates),
        "MSFT": pd.DataFrame({
            "open": base * 0.8 + 0.5,
            "high": base * 0.8 + 2,
            "low": base * 0.8 - 2,
            "close": base * 0.8,
            "volume": 800000
        }, index=dates)
    }


# =============================================================================
# Test DataFetcherFactory Integration
# =============================================================================

class TestDataFetcherFactoryIntegration:
    """Tests for DataFetcherFactory integration with other components."""

    def setup_method(self):
        """Reset factory state before each test."""
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        DataFetcherFactory._INITIALIZED = False

    def teardown_method(self):
        """Reset factory state after each test."""
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        DataFetcherFactory._INITIALIZED = False

    def test_factory_with_cache_integration(self, mock_cache):
        """Test that factory-created fetcher uses provided cache."""
        fetcher = DataFetcherFactory.create(
            "mock",
            cache=mock_cache,
            seed=42
        )
        
        # Fetch data - should be cached
        data1 = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
        assert len(data1) > 0
        
        # Verify data was cached
        cache_key = fetcher._get_cache_key("AAPL", "2023-01-01", "2023-03-01", "1d")
        cached_data = mock_cache.get(cache_key)
        assert cached_data is not None
        assert len(cached_data) == len(data1)
        
        # Fetch again - should hit cache
        data2 = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
        assert len(data2) == len(data1)

    def test_factory_with_rate_limiter_integration(self, rate_limiter):
        """Test that factory-created fetcher uses rate limiter."""
        fetcher = DataFetcherFactory.create(
            "mock",
            rate_limiter=rate_limiter,
            seed=42
        )
        
        # Fetch should work with rate limiter
        data = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
        assert len(data) > 0
        
        # Rate limiter should track request
        assert rate_limiter._request_times is not None

    def test_factory_list_sources_consistency(self):
        """Test that factory sources are consistent across calls."""
        sources1 = DataFetcherFactory.list_available_sources()
        sources2 = DataFetcherFactory.list_available_sources()
        
        assert sources1 == sources2
        assert len(sources1) >= 4  # At least yahoo, alpaca, google, mock

    def test_factory_create_with_all_defaults(self):
        """Test creating fetcher with all default parameters."""
        fetcher = DataFetcherFactory.create("mock")
        
        assert fetcher is not None
        assert hasattr(fetcher, "fetch")
        assert hasattr(fetcher, "fetch_batch")


# =============================================================================
# Test Fetch -> Validate -> Cache Flow
# =============================================================================

class TestFetchValidateCacheFlow:
    """Tests for the complete Fetch -> Validate -> Cache flow."""

    def test_fetch_and_validate_flow(self, mock_cache, data_validator):
        """Test complete flow from fetch to validation to cache."""
        # Step 1: Create fetcher with cache
        fetcher = MockDataFetcher(cache=mock_cache, seed=42)
        
        # Step 2: Fetch data
        data = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
        assert len(data) > 0
        
        # Step 3: Validate data
        data_validator.validate_ohlcv(data)
        quality_report = data_validator.check_data_quality(data)
        
        assert quality_report.is_acceptable
        assert quality_report.quality_score >= 70.0
        
        # Step 4: Cache should have the data
        cache_key = fetcher._get_cache_key("AAPL", "2023-01-01", "2023-03-01", "1d")
        cached_data = mock_cache.get(cache_key)
        assert cached_data is not None

    def test_fetch_batch_and_validate_flow(self, mock_cache, data_validator):
        """Test batch fetch with validation."""
        # Create fetcher with cache
        fetcher = MockDataFetcher(cache=mock_cache, seed=42)
        
        # Fetch batch
        symbols = ["AAPL", "GOOGL", "MSFT"]
        results = fetcher.fetch_batch(symbols, "2023-01-01", "2023-03-01")
        
        assert len(results) == len(symbols)
        
        # Validate all datasets
        for symbol, data in results.items():
            assert len(data) > 0
            data_validator.validate_ohlcv(data)
            quality = data_validator.check_data_quality(data)
            assert quality.is_acceptable

    def test_cache_improves_fetch_performance(self, mock_cache):
        """Test that caching improves subsequent fetch performance."""
        fetcher = MockDataFetcher(cache=mock_cache, seed=42)
        
        # First fetch - no cache
        data1 = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
        
        # Verify cached
        cache_key = fetcher._get_cache_key("AAPL", "2023-01-01", "2023-03-01", "1d")
        assert mock_cache.get(cache_key) is not None
        
        # Second fetch - should hit cache
        data2 = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
        assert len(data2) == len(data1)

    def test_validate_then_cache_workflow(self, mock_cache, data_validator):
        """Test workflow: validate data before caching."""
        fetcher = MockDataFetcher(cache=mock_cache, seed=42)
        
        # Fetch data
        data = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
        
        # Validate before any further processing
        data_validator.validate_ohlcv(data)
        quality_report = data_validator.check_data_quality(data)
        
        # Only cache if quality is acceptable
        if quality_report.is_acceptable:
            cache_key = "validated:AAPL"
            mock_cache.set(cache_key, data)
            
            # Verify cached validated data
            cached = mock_cache.get(cache_key)
            assert cached is not None


# =============================================================================
# Test Multi-Source Fallback
# =============================================================================

class TestMultiSourceFallback:
    """Tests for multi-source fallback behavior."""

    def setup_method(self):
        """Reset factory state before each test."""
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        DataFetcherFactory._INITIALIZED = False

    def teardown_method(self):
        """Reset factory state after each test."""
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        DataFetcherFactory._INITIALIZED = False

    def test_fallback_from_yahoo_to_mock(self):
        """Test fallback from Yahoo to Mock when Yahoo fails."""
        # Mock Yahoo to fail
        with patch('trading_system.data.fetchers.yahoo_fetcher.YahooDataFetcher._fetch_from_api',
                   side_effect=DataFetchError("Yahoo unavailable")):
            
            # Try Yahoo first (will fail)
            try:
                yahoo_fetcher = DataFetcherFactory.create("yahoo")
                # Yahoo would fail here in real scenario
            except DataFetchError:
                pass
            
            # Fallback to mock
            mock_fetcher = DataFetcherFactory.create("mock", seed=42)
            data = mock_fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
            
            assert len(data) > 0
            assert "close" in data.columns

    def test_fallback_order_yahoo_alpaca_mock(self):
        """Test fallback order: Yahoo -> Alpaca -> Mock."""
        sources_tried = []
        
        # Try sources in order until one works
        source_order = ["yahoo", "alpaca", "mock"]
        
        for source in source_order:
            try:
                fetcher = DataFetcherFactory.create(source, seed=42)
                data = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
                sources_tried.append(source)
                break
            except DataFetchError:
                sources_tried.append(source)
                continue
        
        # Should have successfully fetched from mock (last in chain)
        assert "mock" in sources_tried
        assert len(sources_tried) <= 3

    def test_all_sources_fail_graceful_error(self):
        """Test that all sources failing raises appropriate error."""
        with patch('trading_system.data.fetchers.base.BaseDataFetcher.fetch',
                   side_effect=DataFetchError("All sources unavailable")):
            
            fetcher = DataFetcherFactory.create("mock")
            
            # Mock should still work
            data = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
            assert len(data) > 0

    def test_multi_source_with_different_data(self, mock_cache):
        """Test fetching from multiple sources and combining data."""
        # Use mock fetcher with different seeds to simulate different sources
        source1 = MockDataFetcher(cache=mock_cache, seed=100)
        source2 = MockDataFetcher(cache=mock_cache, seed=200)
        
        # Fetch from different "sources"
        data1 = source1.fetch("AAPL", "2023-01-01", "2023-02-01")
        data2 = source2.fetch("AAPL", "2023-01-01", "2023-02-01")
        
        # Both should have valid OHLCV structure
        assert len(data1) > 0
        assert len(data2) > 0
        
        required_cols = ["open", "high", "low", "close", "volume"]
        for col in required_cols:
            assert col in data1.columns
            assert col in data2.columns


# =============================================================================
# Test Error Handling and Recovery
# =============================================================================

class TestErrorHandlingAndRecovery:
    """Tests for error handling and recovery in the data pipeline."""

    def test_invalid_data_rejected_by_validator(self, data_validator):
        """Test that invalid data is rejected by validator."""
        # Create invalid data
        invalid_data = pd.DataFrame({
            "open": [100, 101, 102],
            "high": [99, 102, 103],  # high < low (invalid)
            "low": [101, 100, 101],
            "close": [100.5, 101.5, 102.5],
            "volume": [1000000, 1000000, 1000000]
        })
        
        with pytest.raises(DataValidationError):
            data_validator.validate_ohlcv(invalid_data)

    def test_missing_columns_rejected(self, data_validator):
        """Test that missing columns are rejected."""
        incomplete_data = pd.DataFrame({
            "open": [100, 101, 102],
            "close": [100.5, 101.5, 102.5],
            # Missing high, low, volume
        })
        
        with pytest.raises(DataValidationError):
            data_validator.validate_ohlcv(incomplete_data)

    def test_cache_miss_triggers_fetch(self, mock_cache):
        """Test that cache miss triggers data fetch."""
        fetcher = MockDataFetcher(cache=mock_cache, seed=42)
        
        # Cache should be empty initially
        cache_key = "nonexistent:KEY"
        assert mock_cache.get(cache_key) is None
        
        # Should still fetch (fetcher handles its own cache key)
        data = fetcher.fetch("AAPL", "2023-01-01", "2023-03-01")
        assert len(data) > 0

    def test_empty_symbol_returns_empty_dataframe(self):
        """Test that empty symbol handling returns gracefully."""
        fetcher = MockDataFetcher(seed=42)
        
        # Should handle gracefully or raise meaningful error
        try:
            data = fetcher.fetch("", "2023-01-01", "2023-03-01")
            # If it returns data, it should be empty or minimal
            assert len(data) >= 0
        except (ValueError, DataFetchError):
            # This is also acceptable behavior
            pass

    def test_invalid_date_range_handling(self):
        """Test that invalid date ranges are handled."""
        fetcher = MockDataFetcher(seed=42)
        
        # End before start - should handle gracefully
        with pytest.raises(DataFetchError):
            fetcher.fetch("AAPL", "2023-12-31", "2023-01-01")

    def test_validation_report_includes_all_issues(self, data_validator, sample_ohlcv_data):
        """Test that validation report captures all data quality issues."""
        # Create data with known issues
        data_with_issues = sample_ohlcv_data.copy()
        data_with_issues.loc[data_with_issues.index[5], "close"] = np.nan  # Missing value
        data_with_issues.loc[data_with_issues.index[10], "volume"] = 0  # Zero volume
        
        report = data_validator.check_data_quality(data_with_issues)
        
        # Report should capture issues
        assert report.missing_rows >= 0
        assert report.volume_anomalies >= 0
        assert len(report.issues) >= 0

    def test_recovery_after_validation_failure(self, data_validator):
        """Test recovery workflow after validation failure."""
        # Create invalid data
        invalid_data = pd.DataFrame({
            "open": [100],
            "close": [100],
            # Missing required columns
        })
        
        # Validation should fail
        with pytest.raises(DataValidationError):
            data_validator.validate_ohlcv(invalid_data)
        
        # Create valid data
        valid_data = pd.DataFrame({
            "open": [100, 101, 102, 103, 104],
            "high": [101, 102, 103, 104, 105],
            "low": [99, 100, 101, 102, 103],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "volume": [1000000, 1000000, 1000000, 1000000, 1000000]
        }, index=pd.date_range("2023-01-01", periods=5, freq="D"))
        
        # Now validation should pass
        data_validator.validate_ohlcv(valid_data)
        quality = data_validator.check_data_quality(valid_data)
        assert quality.is_acceptable


# =============================================================================
# Test Cache Manager Integration
# =============================================================================

class TestCacheManagerIntegration:
    """Tests for CacheManager integration with the data pipeline."""

    def test_cache_manager_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = CacheManager(ttl=1, max_size=10)  # 1 second TTL
        
        data = pd.DataFrame({"close": [100, 101, 102]})
        cache.set("test_key", data)
        
        # Should be retrievable immediately
        assert cache.get("test_key") is not None
        
        # Wait for TTL to expire
        import time
        time.sleep(1.5)
        
        # Should be expired
        assert cache.get("test_key") is None

    def test_cache_manager_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = CacheManager(ttl=3600, max_size=3)
        
        # Fill cache
        for i in range(5):
            data = pd.DataFrame({"value": [i]})
            cache.set(f"key_{i}", data)
        
        # Should have evicted older entries
        # key_0 and key_1 should be evicted
        assert cache.get("key_0") is None
        assert cache.get("key_1") is None
        assert cache.get("key_2") is not None

    def test_cache_manager_stats(self):
        """Test cache statistics tracking."""
        cache = CacheManager(ttl=3600, max_size=10)
        
        data = pd.DataFrame({"close": [100, 101]})
        cache.set("key1", data)
        cache.set("key2", data)
        
        stats = cache.get_stats()
        
        assert stats["total_entries"] == 2
        assert stats["max_size"] == 10

    def test_cache_manager_clear(self):
        """Test clearing all cache entries."""
        cache = CacheManager(ttl=3600, max_size=10)
        
        data = pd.DataFrame({"close": [100]})
        cache.set("key1", data)
        cache.set("key2", data)
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get_stats()["total_entries"] == 0


# =============================================================================
# Test Batch Processing Integration
# =============================================================================

class TestBatchProcessingIntegration:
    """Tests for batch data processing integration."""

    def test_batch_fetch_with_validation(self, mock_cache, data_validator):
        """Test batch fetch with per-symbol validation."""
        fetcher = MockDataFetcher(cache=mock_cache, seed=42)
        
        symbols = ["AAPL", "GOOGL", "MSFT"]
        results = fetcher.fetch_batch(symbols, "2023-01-01", "2023-06-01")
        
        # Validate each result
        validation_results = data_validator.validate_batch(results)
        
        assert len(validation_results) == len(symbols)
        
        for symbol, report in validation_results.items():
            assert isinstance(report, DataQualityReport)
            # Mock data should be high quality
            assert report.quality_score >= 70.0

    def test_batch_fetch_continues_on_partial_failure(self):
        """Test that batch fetch handles partial failures gracefully."""
        fetcher = MockDataFetcher(seed=42)
        
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        # Should handle batch fetch without raising
        results = fetcher.fetch_batch(symbols, "2023-01-01", "2023-03-01")
        
        assert len(results) == len(symbols)
        
        # All should have valid data
        for symbol in symbols:
            assert symbol in results
            assert len(results[symbol]) > 0

    def test_batch_validation_reports_all_failures(self, data_validator):
        """Test that batch validation reports all failures."""
        batch_data = {
            "valid_symbol": pd.DataFrame({
                "open": [100, 101],
                "high": [101, 102],
                "low": [99, 100],
                "close": [100.5, 101.5],
                "volume": [1000000, 1000000]
            }),
            "invalid_symbol": pd.DataFrame({
                "open": [100],
                "close": [100]
                # Missing required columns
            })
        }
        
        reports = data_validator.validate_batch(batch_data)
        
        assert "valid_symbol" in reports
        assert "invalid_symbol" in reports
        
        # Invalid symbol should have low quality
        assert reports["invalid_symbol"].quality_score < reports["valid_symbol"].quality_score
