"""Cost benchmarking algorithm implementation."""

import statistics

from pricepoint_intel.intelligence_engine.price_normalization.normalizer import (
    PriceNormalizer,
)
from pricepoint_intel.models.results import CostBenchmark, VendorResult


class CostBenchmarker:
    """Cost benchmarking for competitive position analysis.

    Analyzes vendor pricing data to provide benchmarks and
    competitive positioning insights.
    """

    def __init__(self) -> None:
        """Initialize the cost benchmarker."""
        self._price_normalizer = PriceNormalizer()

    def calculate(
        self,
        vendors: list[VendorResult],
        location: str,
    ) -> CostBenchmark:
        """Calculate cost benchmarks from vendor data.

        Args:
            vendors: List of vendor results with pricing.
            location: Target location for geographic adjustment.

        Returns:
            CostBenchmark with statistical analysis.
        """
        if not vendors:
            raise ValueError("Cannot calculate benchmarks without vendor data")

        prices = [v.price_per_unit for v in vendors]
        sorted_prices = sorted(prices)

        # Calculate percentiles
        n = len(sorted_prices)
        p25_idx = max(0, int(n * 0.25) - 1)
        p50_idx = max(0, int(n * 0.50) - 1)
        p75_idx = max(0, int(n * 0.75) - 1)

        # Calculate geographic premium
        geographic_premium = self._price_normalizer.calculate_geographic_premium(
            location
        )

        # Get the unit from first vendor (assuming consistent units)
        unit = vendors[0].unit if vendors else "unit"

        return CostBenchmark(
            industry_average=round(statistics.mean(prices), 2),
            geographic_premium=geographic_premium,
            percentile_25=sorted_prices[p25_idx],
            percentile_50=sorted_prices[p50_idx],
            percentile_75=sorted_prices[p75_idx],
            unit=unit,
        )

    def get_competitive_position(
        self,
        price: float,
        benchmark: CostBenchmark,
    ) -> dict[str, float | str]:
        """Determine competitive position relative to benchmark.

        Args:
            price: Price to evaluate.
            benchmark: Benchmark to compare against.

        Returns:
            Dictionary with position analysis.
        """
        # Calculate percentile rank
        if price <= benchmark.percentile_25:
            percentile = 25
            position = "low"
        elif price <= benchmark.percentile_50:
            percentile = 50
            position = "below_average"
        elif price <= benchmark.percentile_75:
            percentile = 75
            position = "above_average"
        else:
            percentile = 90
            position = "high"

        # Calculate deviation from industry average
        deviation = (price - benchmark.industry_average) / benchmark.industry_average

        return {
            "percentile_rank": percentile,
            "position": position,
            "deviation_from_average": round(deviation, 4),
            "price_vs_average": round(price - benchmark.industry_average, 2),
        }

    def identify_savings_opportunities(
        self,
        current_price: float,
        benchmark: CostBenchmark,
        target_percentile: int = 25,
    ) -> dict[str, float]:
        """Identify potential cost savings.

        Args:
            current_price: Current purchase price.
            benchmark: Industry benchmark.
            target_percentile: Target percentile to achieve.

        Returns:
            Dictionary with savings analysis.
        """
        target_price = benchmark.percentile_25
        if target_percentile == 50:
            target_price = benchmark.percentile_50
        elif target_percentile == 75:
            target_price = benchmark.percentile_75

        potential_savings = max(0, current_price - target_price)
        savings_percentage = (
            (potential_savings / current_price) * 100 if current_price > 0 else 0
        )

        return {
            "current_price": current_price,
            "target_price": target_price,
            "potential_savings_per_unit": round(potential_savings, 2),
            "savings_percentage": round(savings_percentage, 2),
        }
