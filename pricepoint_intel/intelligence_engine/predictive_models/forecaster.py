"""Price forecasting and trend analysis implementation."""

import math
import random
from dataclasses import dataclass


@dataclass
class PriceForecast:
    """Price forecast result."""

    current_price: float
    forecast_30d: float
    forecast_90d: float
    forecast_180d: float
    confidence_30d: float
    confidence_90d: float
    confidence_180d: float
    trend: str  # "up", "down", "stable"
    volatility: float


class PriceForecaster:
    """Price forecasting and trend prediction model.

    Analyzes historical pricing data to predict future prices
    and identify trends.
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize the price forecaster.

        Args:
            seed: Random seed for reproducible results.
        """
        if seed is not None:
            random.seed(seed)

    def forecast(
        self,
        current_price: float,
        historical_prices: list[float] | None = None,
        seasonality_factor: float = 1.0,
    ) -> PriceForecast:
        """Generate price forecast.

        Args:
            current_price: Current price.
            historical_prices: Optional list of historical prices.
            seasonality_factor: Seasonality adjustment (1.0 = neutral).

        Returns:
            PriceForecast with predictions.
        """
        # Calculate trend from historical data or use default
        if historical_prices and len(historical_prices) >= 3:
            trend_value = self._calculate_trend(historical_prices)
            volatility = self._calculate_volatility(historical_prices)
        else:
            # Default values for demonstration
            trend_value = random.uniform(-0.02, 0.02)  # -2% to +2%
            volatility = random.uniform(0.05, 0.15)

        # Apply seasonality
        seasonal_adjustment = (seasonality_factor - 1.0) * 0.1

        # Calculate forecasts
        forecast_30d = current_price * (1 + trend_value / 12 + seasonal_adjustment)
        forecast_90d = current_price * (1 + trend_value / 4 + seasonal_adjustment)
        forecast_180d = current_price * (1 + trend_value / 2 + seasonal_adjustment)

        # Confidence decreases with time horizon
        confidence_30d = max(0.5, 0.95 - volatility)
        confidence_90d = max(0.4, 0.85 - volatility * 1.5)
        confidence_180d = max(0.3, 0.70 - volatility * 2)

        # Determine trend direction
        if trend_value > 0.01:
            trend = "up"
        elif trend_value < -0.01:
            trend = "down"
        else:
            trend = "stable"

        return PriceForecast(
            current_price=current_price,
            forecast_30d=round(forecast_30d, 2),
            forecast_90d=round(forecast_90d, 2),
            forecast_180d=round(forecast_180d, 2),
            confidence_30d=round(confidence_30d, 2),
            confidence_90d=round(confidence_90d, 2),
            confidence_180d=round(confidence_180d, 2),
            trend=trend,
            volatility=round(volatility, 3),
        )

    def _calculate_trend(self, prices: list[float]) -> float:
        """Calculate price trend from historical data.

        Args:
            prices: List of historical prices (oldest to newest).

        Returns:
            Annualized trend as a decimal.
        """
        if len(prices) < 2:
            return 0.0

        # Simple linear regression slope
        n = len(prices)
        x_mean = (n - 1) / 2
        y_mean = sum(prices) / n

        numerator = sum((i - x_mean) * (prices[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator
        # Annualize the trend (assuming monthly data)
        annualized_trend = slope * 12 / y_mean if y_mean != 0 else 0

        return min(max(annualized_trend, -0.5), 0.5)  # Cap at ±50%

    def _calculate_volatility(self, prices: list[float]) -> float:
        """Calculate price volatility from historical data.

        Args:
            prices: List of historical prices.

        Returns:
            Volatility as a decimal (standard deviation / mean).
        """
        if len(prices) < 2:
            return 0.1

        mean = sum(prices) / len(prices)
        if mean == 0:
            return 0.1

        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)

        return std_dev / mean

    def simulate_promo_lift(
        self,
        current_price: float,
        promo_type: str,
        promo_value: float,
        seasonality_factor: float = 1.0,
        inventory_level: int | None = None,
        competitor_prices: list[float] | None = None,
    ) -> dict:
        """Simulate the lift from a promotional campaign.

        Args:
            current_price: Current product price.
            promo_type: Type of promotion ("volume" or "percentage").
            promo_value: Value of promotion (units or percentage).
            seasonality_factor: Seasonal adjustment factor.
            inventory_level: Current inventory level.
            competitor_prices: List of competitor prices.

        Returns:
            Dictionary with lift projections.
        """
        # Base lift calculation
        if promo_type == "percentage":
            # Percentage discount: higher discount = higher lift
            base_lift = promo_value * 1.5  # 10% discount -> ~15% lift
        else:
            # Volume discount: more units = higher lift
            base_lift = min(promo_value * 0.1, 50)  # Cap at 50%

        # Seasonality adjustment
        seasonal_adjustment = (seasonality_factor - 1.0) * 20

        # Competitor adjustment
        if competitor_prices:
            avg_competitor = sum(competitor_prices) / len(competitor_prices)
            if current_price > avg_competitor:
                # We're more expensive, promo helps more
                competitor_adjustment = min(10, (current_price / avg_competitor - 1) * 50)
            else:
                # We're cheaper, promo helps less
                competitor_adjustment = max(-5, (current_price / avg_competitor - 1) * 25)
        else:
            competitor_adjustment = 0

        # Inventory adjustment
        if inventory_level is not None:
            if inventory_level > 1000:
                inventory_adjustment = 5  # High inventory, need to move
            elif inventory_level < 100:
                inventory_adjustment = -5  # Low inventory, careful
            else:
                inventory_adjustment = 0
        else:
            inventory_adjustment = 0

        # Total projected lift
        projected_lift = max(
            0,
            base_lift + seasonal_adjustment + competitor_adjustment + inventory_adjustment,
        )

        # Confidence interval (wider for extreme values)
        uncertainty = 0.15 + abs(projected_lift - 20) * 0.005
        lower_bound = max(0, projected_lift * (1 - uncertainty))
        upper_bound = projected_lift * (1 + uncertainty)

        # Calculate optimal promo value
        if promo_type == "percentage":
            ai_recommended = min(max(projected_lift / 1.5, 5), 30)  # 5-30% range
        else:
            ai_recommended = min(max(projected_lift * 10, 50), 500)  # 50-500 units

        # Calibration score (how confident is the model)
        calibration_score = max(0.5, 0.9 - uncertainty)

        return {
            "projected_lift": round(projected_lift, 2),
            "confidence_interval": (round(lower_bound, 2), round(upper_bound, 2)),
            "ai_recommended_value": round(ai_recommended, 2),
            "calibration_score": round(calibration_score, 3),
        }
