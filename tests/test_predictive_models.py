"""Tests for the Price Forecaster module."""

from pricepoint_intel.intelligence_engine.predictive_models import PriceForecaster


class TestPriceForecaster:
    """Test suite for PriceForecaster class."""

    def test_forecaster_initialization(self):
        """Test that forecaster initializes correctly."""
        forecaster = PriceForecaster()
        assert forecaster is not None

    def test_forecast_basic(self):
        """Test basic price forecast."""
        forecaster = PriceForecaster(seed=42)
        result = forecaster.forecast(current_price=2.99)

        assert result.current_price == 2.99
        assert result.forecast_30d > 0
        assert result.forecast_90d > 0
        assert result.forecast_180d > 0

    def test_forecast_with_history(self):
        """Test forecast with historical data."""
        forecaster = PriceForecaster(seed=42)
        historical = [2.50, 2.60, 2.70, 2.80, 2.90, 2.99]
        result = forecaster.forecast(
            current_price=2.99,
            historical_prices=historical,
        )

        assert result.trend in ["up", "down", "stable"]
        assert result.volatility >= 0

    def test_forecast_confidence(self):
        """Test that forecast confidence decreases over time."""
        forecaster = PriceForecaster(seed=42)
        result = forecaster.forecast(current_price=2.99)

        assert result.confidence_30d >= result.confidence_90d
        assert result.confidence_90d >= result.confidence_180d

    def test_forecast_with_seasonality(self):
        """Test forecast with seasonality factor."""
        forecaster = PriceForecaster(seed=42)

        result_neutral = forecaster.forecast(
            current_price=2.99,
            seasonality_factor=1.0,
        )
        result_high = forecaster.forecast(
            current_price=2.99,
            seasonality_factor=1.5,
        )

        # High seasonality should increase forecast
        assert result_high.forecast_30d >= result_neutral.forecast_30d

    def test_simulate_promo_lift_percentage(self):
        """Test promo lift simulation with percentage discount."""
        forecaster = PriceForecaster(seed=42)
        result = forecaster.simulate_promo_lift(
            current_price=2.99,
            promo_type="percentage",
            promo_value=15.0,
        )

        assert "projected_lift" in result
        assert "confidence_interval" in result
        assert "ai_recommended_value" in result
        assert "calibration_score" in result

        assert result["projected_lift"] >= 0
        assert result["calibration_score"] >= 0
        assert result["calibration_score"] <= 1

    def test_simulate_promo_lift_volume(self):
        """Test promo lift simulation with volume discount."""
        forecaster = PriceForecaster(seed=42)
        result = forecaster.simulate_promo_lift(
            current_price=2.99,
            promo_type="volume",
            promo_value=100.0,
        )

        assert result["projected_lift"] >= 0

    def test_simulate_promo_with_competitors(self):
        """Test promo simulation with competitor prices."""
        forecaster = PriceForecaster(seed=42)

        # When we're more expensive than competitors
        result_expensive = forecaster.simulate_promo_lift(
            current_price=3.50,
            promo_type="percentage",
            promo_value=10.0,
            competitor_prices=[2.50, 2.75, 3.00],
        )

        # When we're cheaper than competitors
        result_cheap = forecaster.simulate_promo_lift(
            current_price=2.00,
            promo_type="percentage",
            promo_value=10.0,
            competitor_prices=[2.50, 2.75, 3.00],
        )

        # Promo should help more when we're expensive
        assert result_expensive["projected_lift"] >= result_cheap["projected_lift"]

    def test_simulate_promo_with_inventory(self):
        """Test promo simulation with inventory levels."""
        forecaster = PriceForecaster(seed=42)

        # High inventory - need to move
        result_high = forecaster.simulate_promo_lift(
            current_price=2.99,
            promo_type="percentage",
            promo_value=10.0,
            inventory_level=2000,
        )

        # Low inventory - careful
        result_low = forecaster.simulate_promo_lift(
            current_price=2.99,
            promo_type="percentage",
            promo_value=10.0,
            inventory_level=50,
        )

        # High inventory should have higher lift
        assert result_high["projected_lift"] >= result_low["projected_lift"]

    def test_confidence_interval_bounds(self):
        """Test that confidence interval is properly ordered."""
        forecaster = PriceForecaster(seed=42)
        result = forecaster.simulate_promo_lift(
            current_price=2.99,
            promo_type="percentage",
            promo_value=15.0,
        )

        lower, upper = result["confidence_interval"]
        assert lower <= result["projected_lift"] <= upper

    def test_ai_recommended_value_range(self):
        """Test that AI recommended value is in reasonable range."""
        forecaster = PriceForecaster(seed=42)

        # Percentage promo
        result_pct = forecaster.simulate_promo_lift(
            current_price=2.99,
            promo_type="percentage",
            promo_value=15.0,
        )
        assert 5 <= result_pct["ai_recommended_value"] <= 30

        # Volume promo
        result_vol = forecaster.simulate_promo_lift(
            current_price=2.99,
            promo_type="volume",
            promo_value=100.0,
        )
        assert 50 <= result_vol["ai_recommended_value"] <= 500
