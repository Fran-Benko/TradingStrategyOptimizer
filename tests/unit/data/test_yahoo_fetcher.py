"""
Unit tests for Yahoo Finance fetcher.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from trading_system.data.fetchers import YahooDataFetcher
from trading_system.exceptions import DataFetchError


class TestYahooDataFetcher:
    """Tests for YahooDataFetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create fetcher instance for testing."""
        return YahooDataFetcher()

    @pytest.fixture
    def mock_api_response(self):
        """Create mock API response."""
        return {
            "chart": {
                "result": [{
                    "meta": {
                        "symbol": "AAPL",
                        "regularMarketPrice": 150.0
                    },
                    "timestamp": [1704067200, 1704153600, 1704240000],
                    "indicators": {
                        "quote": [{
                            "open": [148.0, 149.0, 150.0],
                            "high": [150.0, 151.0, 152.0],
                            "low": [147.0, 148.0, 149.0],
                            "close": [149.0, 150.0, 151.0],
                            "volume": [1000000, 1100000, 1200000]
                        }],
                        "volume": [{
                            "volume": [1000000, 1100000, 1200000]
                        }]
                    }
                }]
            }
        }

    def test_source_name(self, fetcher):
        """Test that source name is correct."""
        assert fetcher.source_name == "yahoo"

    def test_fetch_with_cache_hit(self, fetcher, mock_cache):
        """Test that cache hit returns cached data."""
        fetcher.cache = mock_cache
        data = pd.DataFrame({
            "open": [148.0],
            "high": [150.0],
            "low": [147.0],
            "close": [149.0],
            "volume": [1000000]
        })
        mock_cache.set("yahoo:AAPL:2023-01-01:2023-01-10:1d", data)
        
        result = fetcher.fetch("AAPL", "2023-01-01", "2023-01-10")
        
        assert result.equals(data)

    @patch("requests.Session.get")
    def test_fetch_from_api(self, mock_get, fetcher, mock_api_response):
        """Test fetching data from API."""
        mock_response = Mock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        data = fetcher.fetch("AAPL", "2023-01-01", "2023-01-10")
        
        assert isinstance(data, pd.DataFrame)
        assert "close" in data.columns
        assert len(data) == 3

    @patch("requests.Session.get")
    def test_fetch_with_invalid_symbol(self, mock_get, fetcher):
        """Test fetch with invalid symbol raises error."""
        mock_response = Mock()
        mock_response.json.return_value = {"chart": {"result": None}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(DataFetchError):
            fetcher.fetch("INVALID", "2023-01-01", "2023-01-10")

    @patch("requests.Session.get")
    def test_fetch_raises_on_network_error(self, mock_get, fetcher):
        """Test that network errors raise DataFetchError."""
        mock_get.side_effect = ConnectionError("Network error")
        
        with pytest.raises(DataFetchError, match="Failed to fetch"):
            fetcher.fetch("AAPL", "2023-01-01", "2023-01-10")

    def test_normalize_interval(self, fetcher):
        """Test interval normalization."""
        assert fetcher._normalize_interval("1d") == "1d"
        assert fetcher._normalize_interval("1h") == "1h"
        assert fetcher._normalize_interval("5m") == "5m"
        assert fetcher._normalize_interval("unknown") == "1d"

    @patch("requests.Session.get")
    def test_fetch_batch(self, mock_get, fetcher, mock_api_response):
        """Test batch fetching."""
        mock_response = Mock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        results = fetcher.fetch_batch(["AAPL", "GOOGL"], "2023-01-01", "2023-01-10")
        
        assert isinstance(results, dict)
        assert "AAPL" in results
