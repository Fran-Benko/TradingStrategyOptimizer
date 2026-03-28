"""
Data fetcher factory.

Provides factory methods for creating data fetcher instances
and managing available data sources.
"""

from typing import Any, Dict, List, Optional, Type

from trading_system.data.fetchers.base import BaseDataFetcher
from trading_system.exceptions import ConfigurationError


class DataFetcherFactory:
    """
    Factory for creating data fetcher instances.

    Supports multiple data sources with consistent interface.
    Factory is extensible for adding new sources.

    Example:
        >>> factory = DataFetcherFactory()
        >>> fetcher = factory.create('yahoo')
        >>> data = fetcher.fetch('AAPL', '2023-01-01', '2023-12-31')

        >>> # List available sources
        >>> sources = factory.list_available_sources()
        >>> print(sources)  # ['yahoo', 'alpaca', 'google', 'mock']
    """

    _FETCHER_REGISTRY: Dict[str, Type[BaseDataFetcher]] = {}
    _INITIALIZED = False

    @classmethod
    def register(cls, name: str, fetcher_class: Type[BaseDataFetcher]) -> None:
        """
        Register a new fetcher class.

        Args:
            name: Source name (e.g., 'yahoo', 'alpaca')
            fetcher_class: Fetcher class to register

        Raises:
            TypeError: If fetcher_class is not a BaseDataFetcher subclass
        """
        if not issubclass(fetcher_class, BaseDataFetcher):
            raise TypeError(
                f"{fetcher_class.__name__} must be a subclass of BaseDataFetcher"
            )
        cls._FETCHER_REGISTRY[name.lower()] = fetcher_class
        cls._INITIALIZED = True

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure default fetchers are registered."""
        if cls._INITIALIZED:
            return

        from trading_system.data.fetchers.yahoo_fetcher import YahooDataFetcher
        from trading_system.data.fetchers.alpaca_fetcher import AlpacaDataFetcher
        from trading_system.data.fetchers.google_finance import GoogleFinanceFetcher
        from trading_system.data.fetchers.mock_fetcher import MockDataFetcher

        cls.register("yahoo", YahooDataFetcher)
        cls.register("alpaca", AlpacaDataFetcher)
        cls.register("google", GoogleFinanceFetcher)
        cls.register("mock", MockDataFetcher)
        cls._INITIALIZED = True

    @classmethod
    def create(
        cls,
        source: str = "yahoo",
        **kwargs: Any
    ) -> BaseDataFetcher:
        """
        Create a fetcher instance by source name.

        Args:
            source: Source name ('yahoo', 'alpaca', 'google', 'mock')
            **kwargs: Additional arguments passed to fetcher constructor

        Returns:
            Fetcher instance

        Raises:
            ConfigurationError: If source is not supported
        """
        cls._ensure_initialized()

        source_lower = source.lower()

        if source_lower not in cls._FETCHER_REGISTRY:
            available = list(cls._FETCHER_REGISTRY.keys())
            raise ConfigurationError(
                parameter="source",
                reason=f"Unknown source '{source}'. Available: {available}"
            )

        fetcher_class = cls._FETCHER_REGISTRY[source_lower]

        return fetcher_class(**kwargs)

    @classmethod
    def get_fetcher(cls, source: str, **kwargs: Any) -> BaseDataFetcher:
        """
        Get a fetcher instance (alias for create).

        Args:
            source: Source name
            **kwargs: Additional arguments passed to fetcher constructor

        Returns:
            Fetcher instance
        """
        return cls.create(source, **kwargs)

    @classmethod
    def list_available_sources(cls) -> List[str]:
        """
        List all supported data sources.

        Returns:
            List of source names
        """
        cls._ensure_initialized()
        return sorted(cls._FETCHER_REGISTRY.keys())

    @classmethod
    def is_source_available(cls, source: str) -> bool:
        """
        Check if a source is available.

        Args:
            source: Source name to check

        Returns:
            True if source is registered, False otherwise
        """
        cls._ensure_initialized()
        return source.lower() in cls._FETCHER_REGISTRY

    @classmethod
    def get_fetcher_info(cls, source: str) -> Dict[str, Any]:
        """
        Get information about a fetcher source.

        Args:
            source: Source name

        Returns:
            Dictionary with fetcher metadata

        Raises:
            ConfigurationError: If source is not available
        """
        cls._ensure_initialized()

        source_lower = source.lower()

        if source_lower not in cls._FETCHER_REGISTRY:
            available = list(cls._FETCHER_REGISTRY.keys())
            raise ConfigurationError(
                parameter="source",
                reason=f"Unknown source '{source}'. Available: {available}"
            )

        fetcher_class = cls._FETCHER_REGISTRY[source_lower]

        return {
            "name": source_lower,
            "class": fetcher_class.__name__,
            "module": fetcher_class.__module__,
            "doc": fetcher_class.__doc__.strip() if fetcher_class.__doc__ else ""
        }

    @classmethod
    def validate_config(cls, source: str, **kwargs: Any) -> bool:
        """
        Validate configuration for a source.

        Args:
            source: Source name
            **kwargs: Configuration to validate

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        cls._ensure_initialized()

        source_lower = source.lower()

        if source_lower not in cls._FETCHER_REGISTRY:
            available = list(cls._FETCHER_REGISTRY.keys())
            raise ConfigurationError(
                parameter="source",
                reason=f"Unknown source '{source}'. Available: {available}"
            )

        return True


def create_fetcher(source: str = "yahoo", **kwargs: Any) -> BaseDataFetcher:
    """
    Convenience function to create a fetcher.

    Args:
        source: Source name
        **kwargs: Additional arguments

    Returns:
        Fetcher instance
    """
    return DataFetcherFactory.create(source, **kwargs)


def get_fetcher(source: str, **kwargs: Any) -> BaseDataFetcher:
    """
    Convenience function to get a fetcher.

    Args:
        source: Source name
        **kwargs: Additional arguments

    Returns:
        Fetcher instance
    """
    return DataFetcherFactory.get_fetcher(source, **kwargs)


def list_sources() -> List[str]:
    """
    Convenience function to list available sources.

    Returns:
        List of source names
    """
    return DataFetcherFactory.list_available_sources()
