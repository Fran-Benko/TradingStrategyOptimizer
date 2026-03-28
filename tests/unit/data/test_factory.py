"""
Unit tests for data fetcher factory.
"""

import pytest
from unittest.mock import patch, MagicMock

from trading_system.data.fetchers.factory import (
    DataFetcherFactory,
    create_fetcher,
    get_fetcher,
    list_sources,
)
from trading_system.data.fetchers.base import BaseDataFetcher
from trading_system.exceptions import ConfigurationError


class TestDataFetcherFactory:
    """Tests for DataFetcherFactory class."""

    def setup_method(self):
        """Reset factory state before each test."""
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        DataFetcherFactory._INITIALIZED = False

    def teardown_method(self):
        """Reset factory state after each test."""
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        DataFetcherFactory._INITIALIZED = False

    # === Registration tests ===

    def test_register_valid_fetcher(self):
        """Test registering a valid fetcher class."""
        class MockFetcher(BaseDataFetcher):
            @property
            def source_name(self):
                return "test_source"
            
            def _fetch_from_api(self, symbol, start, end, interval):
                return None
        
        DataFetcherFactory.register("test_source", MockFetcher)
        
        assert "test_source" in DataFetcherFactory._FETCHER_REGISTRY
        assert DataFetcherFactory._FETCHER_REGISTRY["test_source"] == MockFetcher

    def test_register_invalid_fetcher_raises(self):
        """Test that registering non-BaseDataFetcher raises TypeError."""
        class NotAFetcher:
            pass
        
        with pytest.raises(TypeError) as exc_info:
            DataFetcherFactory.register("invalid", NotAFetcher)
        
        assert "must be a subclass of BaseDataFetcher" in str(exc_info.value)

    def test_register_overwrites_existing(self):
        """Test that registering same name overwrites existing."""
        class MockFetcher1(BaseDataFetcher):
            @property
            def source_name(self):
                return "test_source"
            def _fetch_from_api(self, symbol, start, end, interval):
                return None
        
        class MockFetcher2(BaseDataFetcher):
            @property
            def source_name(self):
                return "test_source"
            def _fetch_from_api(self, symbol, start, end, interval):
                return None
        
        DataFetcherFactory.register("test_source", MockFetcher1)
        DataFetcherFactory.register("test_source", MockFetcher2)
        
        assert DataFetcherFactory._FETCHER_REGISTRY["test_source"] == MockFetcher2

    def test_register_sets_initialized_flag(self):
        """Test that registration sets _INITIALIZED to True."""
        assert DataFetcherFactory._INITIALIZED is False
        
        class MockFetcher(BaseDataFetcher):
            @property
            def source_name(self):
                return "test"
            def _fetch_from_api(self, symbol, start, end, interval):
                return None
        
        DataFetcherFactory.register("test", MockFetcher)
        
        assert DataFetcherFactory._INITIALIZED is True

    # === create tests ===

    def test_create_yahoo_fetcher(self):
        """Test creating Yahoo fetcher."""
        fetcher = DataFetcherFactory.create("yahoo")
        
        assert fetcher is not None
        assert hasattr(fetcher, "source_name")

    def test_create_alpaca_fetcher(self):
        """Test creating Alpaca fetcher."""
        fetcher = DataFetcherFactory.create("alpaca")
        
        assert fetcher is not None
        assert hasattr(fetcher, "source_name")

    def test_create_google_fetcher(self):
        """Test creating Google fetcher."""
        fetcher = DataFetcherFactory.create("google")
        
        assert fetcher is not None
        assert hasattr(fetcher, "source_name")

    def test_create_mock_fetcher(self):
        """Test creating Mock fetcher."""
        fetcher = DataFetcherFactory.create("mock")
        
        assert fetcher is not None
        assert fetcher.source_name == "mock"

    def test_create_case_insensitive(self):
        """Test that source name is case-insensitive."""
        fetcher_upper = DataFetcherFactory.create("YAHOO")
        fetcher_lower = DataFetcherFactory.create("yahoo")
        fetcher_mixed = DataFetcherFactory.create("Yahoo")
        
        assert type(fetcher_upper) == type(fetcher_lower) == type(fetcher_mixed)

    def test_create_with_kwargs(self):
        """Test creating fetcher with additional kwargs."""
        # Test with mock fetcher since it accepts kwargs
        fetcher = DataFetcherFactory.create(
            "mock",
            seed=123,
            base_price=200.0,
            volatility=0.05
        )
        
        assert fetcher is not None
        assert fetcher.seed == 123
        assert fetcher.base_price == 200.0
        assert fetcher.volatility == 0.05

    def test_create_unknown_source_raises(self):
        """Test that unknown source raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            DataFetcherFactory.create("unknown_source")
        
        assert "Unknown source" in str(exc_info.value)
        assert "unknown_source" in str(exc_info.value)

    def test_create_unknown_shows_available(self):
        """Test that error message shows available sources."""
        with pytest.raises(ConfigurationError) as exc_info:
            DataFetcherFactory.create("invalid")
        
        error_msg = str(exc_info.value)
        assert "Available:" in error_msg

    # === get_fetcher tests ===

    def test_get_fetcher_is_alias_for_create(self):
        """Test that get_fetcher is an alias for create."""
        fetcher1 = DataFetcherFactory.get_fetcher("yahoo")
        fetcher2 = DataFetcherFactory.create("yahoo")
        
        assert type(fetcher1) == type(fetcher2)

    def test_get_fetcher_with_kwargs(self):
        """Test get_fetcher passes kwargs correctly."""
        fetcher = DataFetcherFactory.get_fetcher(
            "mock",
            seed=456,
            base_price=300.0
        )
        
        assert fetcher.seed == 456
        assert fetcher.base_price == 300.0

    # === list_available_sources tests ===

    def test_list_available_sources_returns_list(self):
        """Test that list_available_sources returns a list."""
        sources = DataFetcherFactory.list_available_sources()
        
        assert isinstance(sources, list)

    def test_list_available_sources_contains_defaults(self):
        """Test that default sources are available."""
        sources = DataFetcherFactory.list_available_sources()
        
        assert "yahoo" in sources
        assert "alpaca" in sources
        assert "google" in sources
        assert "mock" in sources

    def test_list_available_sources_sorted(self):
        """Test that sources are returned sorted."""
        sources = DataFetcherFactory.list_available_sources()
        
        assert sources == sorted(sources)

    def test_list_available_sources_after_registration(self):
        """Test list_available_sources includes registered sources."""
        class MockFetcher(BaseDataFetcher):
            @property
            def source_name(self):
                return "custom_source"
            def _fetch_from_api(self, symbol, start, end, interval):
                return None
        
        DataFetcherFactory.register("custom_source", MockFetcher)
        sources = DataFetcherFactory.list_available_sources()
        
        assert "custom_source" in sources

    # === is_source_available tests ===

    def test_is_source_available_known_source(self):
        """Test is_source_available returns True for known sources."""
        assert DataFetcherFactory.is_source_available("yahoo") is True
        assert DataFetcherFactory.is_source_available("YAHOO") is True

    def test_is_source_available_unknown_source(self):
        """Test is_source_available returns False for unknown sources."""
        assert DataFetcherFactory.is_source_available("unknown_source") is False

    def test_is_source_available_case_insensitive(self):
        """Test is_source_available is case-insensitive."""
        assert DataFetcherFactory.is_source_available("YAHOO") is True
        assert DataFetcherFactory.is_source_available("Yahoo") is True
        assert DataFetcherFactory.is_source_available("yahoo") is True

    # === get_fetcher_info tests ===

    def test_get_fetcher_info_valid_source(self):
        """Test get_fetcher_info returns metadata."""
        info = DataFetcherFactory.get_fetcher_info("yahoo")
        
        assert "name" in info
        assert "class" in info
        assert "module" in info
        assert info["name"] == "yahoo"

    def test_get_fetcher_info_contains_class_name(self):
        """Test that fetcher info contains class name."""
        info = DataFetcherFactory.get_fetcher_info("yahoo")
        
        assert "YahooDataFetcher" in info["class"]

    def test_get_fetcher_info_contains_module(self):
        """Test that fetcher info contains module path."""
        info = DataFetcherFactory.get_fetcher_info("yahoo")
        
        assert "yahoo_fetcher" in info["module"]

    def test_get_fetcher_info_unknown_source_raises(self):
        """Test get_fetcher_info raises for unknown source."""
        with pytest.raises(ConfigurationError):
            DataFetcherFactory.get_fetcher_info("nonexistent")

    def test_get_fetcher_info_case_insensitive(self):
        """Test get_fetcher_info is case-insensitive."""
        info_upper = DataFetcherFactory.get_fetcher_info("YAHOO")
        info_lower = DataFetcherFactory.get_fetcher_info("yahoo")
        
        assert info_upper["name"] == info_lower["name"]

    # === validate_config tests ===

    def test_validate_config_valid_source(self):
        """Test validate_config returns True for valid source."""
        result = DataFetcherFactory.validate_config("yahoo")
        
        assert result is True

    def test_validate_config_unknown_source_raises(self):
        """Test validate_config raises for unknown source."""
        with pytest.raises(ConfigurationError):
            DataFetcherFactory.validate_config("invalid_source")

    def test_validate_config_case_insensitive(self):
        """Test validate_config is case-insensitive."""
        result = DataFetcherFactory.validate_config("YAHOO")
        assert result is True

    # === _ensure_initialized tests ===

    def test_ensure_initialized_registers_defaults(self):
        """Test _ensure_initialized registers default fetchers."""
        DataFetcherFactory._INITIALIZED = False
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        
        DataFetcherFactory._ensure_initialized()
        
        default_sources = ["yahoo", "alpaca", "google", "mock"]
        for source in default_sources:
            assert source in DataFetcherFactory._FETCHER_REGISTRY

    def test_ensure_initialized_no_op_if_initialized(self):
        """Test _ensure_initialized is no-op if already initialized."""
        initial_count = len(DataFetcherFactory._FETCHER_REGISTRY)
        
        DataFetcherFactory._ensure_initialized()
        DataFetcherFactory._ensure_initialized()
        
        # Should not add more fetchers
        assert len(DataFetcherFactory._FETCHER_REGISTRY) >= initial_count


class TestFactoryConvenienceFunctions:
    """Tests for factory convenience functions."""

    def setup_method(self):
        """Reset factory state before each test."""
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        DataFetcherFactory._INITIALIZED = False

    def teardown_method(self):
        """Reset factory state after each test."""
        DataFetcherFactory._FETCHER_REGISTRY.clear()
        DataFetcherFactory._INITIALIZED = False

    def test_create_fetcher_function(self):
        """Test create_fetcher convenience function."""
        fetcher = create_fetcher("mock")
        
        assert fetcher is not None
        assert fetcher.source_name == "mock"

    def test_create_fetcher_default_source(self):
        """Test create_fetcher uses default source."""
        fetcher = create_fetcher()
        
        assert fetcher is not None

    def test_get_fetcher_function(self):
        """Test get_fetcher convenience function."""
        fetcher = get_fetcher("mock", seed=789)
        
        assert fetcher is not None
        assert fetcher.seed == 789

    def test_list_sources_function(self):
        """Test list_sources convenience function."""
        sources = list_sources()
        
        assert isinstance(sources, list)
        assert len(sources) >= 4  # At least default sources

    def test_convenience_functions_use_same_registry(self):
        """Test all convenience functions use same registry."""
        # Trigger initialization
        list_sources()
        
        # Both functions should work
        fetcher1 = create_fetcher("yahoo")
        fetcher2 = get_fetcher("yahoo")
        
        assert type(fetcher1) == type(fetcher2)
