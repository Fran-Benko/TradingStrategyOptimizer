"""
Unit tests for Bollinger Bands strategy.
"""

import pytest
import pandas as pd
import numpy as np

from trading_system.strategies.mean_reversion.bollinger_strategy import (
    BollingerBandsStrategy,
    BollingerBandsStrategyConfig,
)


class TestBollingerBandsStrategyConfig:
    """Tests for BollingerBandsStrategyConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BollingerBandsStrategyConfig()
        
        assert config.period == 20
        assert config.num_std == 2.0
        assert config.exit_mode == "middle"
        assert config.position_size == 1.0
        assert config.use_trailing_stop is False
        assert config.trailing_stop_pct == 0.02

    def test_custom_config(self):
        """Test custom configuration."""
        config = BollingerBandsStrategyConfig(
            period=30,
            num_std=2.5,
            exit_mode="upper",
            position_size=0.5,
            use_trailing_stop=True,
            trailing_stop_pct=0.03
        )
        
        assert config.period == 30
        assert config.num_std == 2.5
        assert config.exit_mode == "upper"
        assert config.position_size == 0.5
        assert config.use_trailing_stop is True
        assert config.trailing_stop_pct == 0.03

    def test_config_validation_period_too_low(self):
        """Test validation fails when period < 5."""
        with pytest.raises(ValueError, match="Period must be between 5 and 200"):
            BollingerBandsStrategyConfig(period=4)

    def test_config_validation_period_too_high(self):
        """Test validation fails when period > 200."""
        with pytest.raises(ValueError, match="Period must be between 5 and 200"):
            BollingerBandsStrategyConfig(period=201)

    def test_config_validation_num_std_too_low(self):
        """Test validation fails when num_std < 0.5."""
        with pytest.raises(ValueError, match="Num_std must be between 0.5 and 4.0"):
            BollingerBandsStrategyConfig(num_std=0.4)

    def test_config_validation_num_std_too_high(self):
        """Test validation fails when num_std > 4.0."""
        with pytest.raises(ValueError, match="Num_std must be between 0.5 and 4.0"):
            BollingerBandsStrategyConfig(num_std=4.1)

    def test_config_validation_invalid_exit_mode(self):
        """Test validation fails for invalid exit mode."""
        with pytest.raises(ValueError, match="Exit mode must be 'middle' or 'upper'"):
            BollingerBandsStrategyConfig(exit_mode="invalid")

    def test_config_validation_position_size_zero(self):
        """Test validation fails when position_size <= 0."""
        with pytest.raises(ValueError, match="Position size must be positive"):
            BollingerBandsStrategyConfig(position_size=0)

    def test_config_validation_trailing_stop_pct_too_low(self):
        """Test validation fails when trailing stop pct < 0.001."""
        with pytest.raises(ValueError, match="Trailing stop percentage must be between"):
            BollingerBandsStrategyConfig(
                use_trailing_stop=True,
                trailing_stop_pct=0.0005
            )

    def test_config_validation_trailing_stop_pct_too_high(self):
        """Test validation fails when trailing stop pct > 0.5."""
        with pytest.raises(ValueError, match="Trailing stop percentage must be between"):
            BollingerBandsStrategyConfig(
                use_trailing_stop=True,
                trailing_stop_pct=0.6
            )


class TestBollingerBandsStrategy:
    """Tests for BollingerBandsStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create Bollinger Bands strategy instance."""
        return BollingerBandsStrategy()

    @pytest.fixture
    def custom_strategy(self):
        """Create Bollinger Bands strategy with custom config."""
        config = BollingerBandsStrategyConfig(
            period=30,
            num_std=2.5,
            exit_mode="upper"
        )
        return BollingerBandsStrategy(config)

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data."""
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

    def test_init_default_config(self, strategy):
        """Test initialization with default config."""
        assert strategy.period == 20
        assert strategy.num_std == 2.0
        assert strategy.exit_mode == "middle"
        assert strategy.position_size == 1.0
        assert strategy.use_trailing_stop is False

    def test_init_custom_config(self, custom_strategy):
        """Test initialization with custom config."""
        assert custom_strategy.period == 30
        assert custom_strategy.num_std == 2.5
        assert custom_strategy.exit_mode == "upper"

    def test_required_columns(self, strategy):
        """Test required columns."""
        assert strategy.required_columns == ["close"]

    def test_min_periods(self, strategy):
        """Test minimum periods calculation."""
        # min_periods = period + 2 = 20 + 2 = 22
        assert strategy.min_periods == 22

    def test_min_periods_custom(self, custom_strategy):
        """Test min periods with custom config."""
        # min_periods = period + 2 = 30 + 2 = 32
        assert custom_strategy.min_periods == 32

    def test_generate_signals_returns_array(self, strategy, sample_data):
        """Test that generate_signals returns numpy array."""
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)

    def test_generate_signals_values(self, strategy, sample_data):
        """Test that signals are valid (-1, 0, 1)."""
        signals = strategy.generate_signals(sample_data)

        assert set(signals).issubset({-1, 0, 1})

    def test_generate_signals_with_insufficient_data(self, strategy):
        """Test with insufficient data raises error."""
        small_data = pd.DataFrame({
            "close": [100, 101, 102, 103, 104]
        })

        with pytest.raises(ValueError, match="Insufficient data"):
            strategy.generate_signals(small_data)

    def test_generate_signals_with_missing_columns(self, strategy):
        """Test with missing columns raises error."""
        incomplete_data = pd.DataFrame({"open": [100, 101, 102]})

        with pytest.raises(ValueError, match="Missing required columns"):
            strategy.generate_signals(incomplete_data)

    def test_get_indicator_upper_band(self, strategy, sample_data):
        """Test getting upper band indicator."""
        strategy.generate_signals(sample_data)

        upper_band = strategy.get_indicator("upper_band")

        assert upper_band is not None
        assert len(upper_band) == len(sample_data)

    def test_get_indicator_middle_band(self, strategy, sample_data):
        """Test getting middle band indicator."""
        strategy.generate_signals(sample_data)

        middle_band = strategy.get_indicator("middle_band")

        assert middle_band is not None
        assert len(middle_band) == len(sample_data)

    def test_get_indicator_lower_band(self, strategy, sample_data):
        """Test getting lower band indicator."""
        strategy.generate_signals(sample_data)

        lower_band = strategy.get_indicator("lower_band")

        assert lower_band is not None
        assert len(lower_band) == len(sample_data)

    def test_get_indicator_bandwidth(self, strategy, sample_data):
        """Test getting bandwidth indicator."""
        strategy.generate_signals(sample_data)

        bandwidth = strategy.get_indicator("bandwidth")

        assert bandwidth is not None
        assert len(bandwidth) == len(sample_data)
        assert (bandwidth.dropna() >= 0).all()  # Bandwidth should be non-negative (excluding NaN)

    def test_get_indicator_nonexistent(self, strategy, sample_data):
        """Test getting nonexistent indicator returns None."""
        strategy.generate_signals(sample_data)

        indicator = strategy.get_indicator("nonexistent")

        assert indicator is None

    def test_get_parameters(self, strategy):
        """Test getting strategy parameters."""
        params = strategy.get_parameters()

        assert "period" in params
        assert "num_std" in params
        assert "exit_mode" in params
        assert params["period"] == 20
        assert params["num_std"] == 2.0

    def test_should_exit_middle_mode(self, strategy, sample_data):
        """Test _should_exit with middle exit mode."""
        # Create strategy with middle exit mode
        config = BollingerBandsStrategyConfig(exit_mode="middle")
        strat = BollingerBandsStrategy(config)
        
        # Test exit when price reaches middle band
        assert strat._should_exit(
            current_price=100,
            middle_band=100,
            upper_band=110,
            highest_price=100
        ) is True
        
        # Test no exit when price below middle band
        assert strat._should_exit(
            current_price=95,
            middle_band=100,
            upper_band=110,
            highest_price=95
        ) is False

    def test_should_exit_upper_mode(self, strategy, sample_data):
        """Test _should_exit with upper exit mode."""
        config = BollingerBandsStrategyConfig(exit_mode="upper")
        strat = BollingerBandsStrategy(config)
        
        # Test exit when price reaches upper band
        assert strat._should_exit(
            current_price=110,
            middle_band=100,
            upper_band=110,
            highest_price=110
        ) is True
        
        # Test no exit when price below upper band
        assert strat._should_exit(
            current_price=105,
            middle_band=100,
            upper_band=110,
            highest_price=105
        ) is False

    def test_should_exit_trailing_stop(self, strategy, sample_data):
        """Test _should_exit with trailing stop enabled."""
        config = BollingerBandsStrategyConfig(
            use_trailing_stop=True,
            trailing_stop_pct=0.02
        )
        strat = BollingerBandsStrategy(config)
        
        # Price drops below trailing stop
        assert strat._should_exit(
            current_price=97,  # 100 * (1 - 0.03) = 97
            middle_band=100,
            upper_band=110,
            highest_price=100
        ) is True
        
        # Price still above trailing stop
        assert strat._should_exit(
            current_price=99,
            middle_band=100,
            upper_band=110,
            highest_price=100
        ) is False

    def test_trailing_stop_with_higher_high(self, strategy, sample_data):
        """Test trailing stop updates with higher prices."""
        config = BollingerBandsStrategyConfig(
            use_trailing_stop=True,
            trailing_stop_pct=0.05,
            exit_mode="upper"  # Use upper band to isolate trailing stop behavior
        )
        strat = BollingerBandsStrategy(config)
        
        # Price 105 is above trailing stop (104.5) and below upper band (110), no exit
        assert strat._should_exit(
            current_price=105,
            middle_band=100,
            upper_band=110,
            highest_price=110
        ) is False
        
        # Price 104 is below trailing stop (104.5), should exit
        assert strat._should_exit(
            current_price=104,
            middle_band=100,
            upper_band=110,
            highest_price=110
        ) is True

    def test_repr(self, strategy):
        """Test string representation."""
        repr_str = repr(strategy)

        assert "BollingerBandsStrategy" in repr_str
        assert "period" in repr_str

    def test_exit_mode_middle(self, strategy, sample_data):
        """Test strategy with middle exit mode."""
        config = BollingerBandsStrategyConfig(exit_mode="middle")
        strat = BollingerBandsStrategy(config)
        
        signals = strat.generate_signals(sample_data)
        
        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)
        assert set(signals).issubset({-1, 0, 1})

    def test_exit_mode_upper(self, strategy, sample_data):
        """Test strategy with upper exit mode."""
        config = BollingerBandsStrategyConfig(exit_mode="upper")
        strat = BollingerBandsStrategy(config)
        
        signals = strat.generate_signals(sample_data)
        
        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(sample_data)
        assert set(signals).issubset({-1, 0, 1})
