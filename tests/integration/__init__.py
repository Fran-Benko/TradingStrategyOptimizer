"""
Integration tests for the trading system.

Tests the integration between multiple components of the trading system,
including data fetching, validation, caching, strategy execution,
optimization, and backtesting.

Test modules:
- test_data_pipeline: Data fetching, caching, and validation
- test_strategy_execution: Strategy initialization, signal generation, and backtesting
- test_backtest_flow: Fetch data, run strategies, compare results, walk-forward analysis
- test_end_to_end: Complete workflow from fetch to report

Run all integration tests:
    pytest tests/integration/ -v

Run specific test:
    pytest tests/integration/test_data_pipeline.py -v
"""

__version__ = "0.1.0"
