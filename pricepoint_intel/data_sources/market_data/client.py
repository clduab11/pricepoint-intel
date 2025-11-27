"""Market data client for industry benchmarks and indices."""

from dataclasses import dataclass
from typing import Any


@dataclass
class IndustryBenchmark:
    """Industry benchmark data."""

    industry_code: str
    industry_name: str
    average_price: float
    price_range: tuple[float, float]
    unit: str
    sample_size: int
    data_date: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "average_price": self.average_price,
            "price_range": self.price_range,
            "unit": self.unit,
            "sample_size": self.sample_size,
            "data_date": self.data_date,
        }


@dataclass
class PriceIndex:
    """Price index data point."""

    index_name: str
    date: str
    value: float
    change_pct: float
    base_year: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "index_name": self.index_name,
            "date": self.date,
            "value": self.value,
            "change_pct": self.change_pct,
            "base_year": self.base_year,
        }


class MarketDataClient:
    """Client for market data and industry benchmarks.

    Provides access to industry benchmarks, price indices,
    and market research data.
    """

    # Industry codes for flooring products
    INDUSTRY_CODES = {
        "flooring": "238330",
        "laminate": "238331",
        "hardwood": "238332",
        "vinyl": "238333",
        "tile": "238334",
        "carpet": "238335",
    }

    def __init__(self) -> None:
        """Initialize the market data client."""
        pass

    async def get_industry_benchmark(
        self,
        product_category: str,
    ) -> IndustryBenchmark | None:
        """Get industry benchmark for a product category.

        Args:
            product_category: Product category name.

        Returns:
            IndustryBenchmark if found, None otherwise.
        """
        category_lower = product_category.lower()

        # Default benchmarks based on category
        benchmarks = {
            "laminate flooring": (2.67, (1.89, 4.23), "sqft"),
            "hardwood flooring": (5.50, (3.00, 12.00), "sqft"),
            "vinyl flooring": (3.25, (1.50, 6.00), "sqft"),
            "tile flooring": (4.00, (2.00, 15.00), "sqft"),
            "carpet": (2.50, (1.00, 8.00), "sqft"),
        }

        for category, (avg, range_, unit) in benchmarks.items():
            if category in category_lower or category_lower in category:
                return IndustryBenchmark(
                    industry_code=self.INDUSTRY_CODES.get(
                        category.split()[0], "238330"
                    ),
                    industry_name=category.title(),
                    average_price=avg,
                    price_range=range_,
                    unit=unit,
                    sample_size=500,
                    data_date="2024-01-15",
                )

        return None

    async def get_price_index(
        self,
        index_name: str = "PPI-Flooring",
        months: int = 12,
    ) -> list[PriceIndex]:
        """Get price index history.

        Args:
            index_name: Name of the price index.
            months: Number of months of history.

        Returns:
            List of PriceIndex data points.
        """
        # In production, this would fetch from BLS or other sources
        base_value = 100.0

        return [
            PriceIndex(
                index_name=index_name,
                date=f"2024-{12-i:02d}-01",
                value=base_value + i * 0.5,
                change_pct=0.5 if i > 0 else 0.0,
                base_year=2020,
            )
            for i in range(min(months, 12))
        ]

    async def get_regional_cost_factors(
        self,
        location: str,
    ) -> dict[str, float]:
        """Get regional cost adjustment factors.

        Args:
            location: Location code (zip or state).

        Returns:
            Dictionary of cost factors.
        """
        # In production, this would use BLS regional data
        # Simplified regional factors
        if location.startswith(("0", "1", "2")):
            region = "northeast"
            factor = 1.15
        elif location.startswith("3"):
            region = "southeast"
            factor = 0.95
        elif location.startswith(("4", "5", "6")):
            region = "midwest"
            factor = 0.92
        elif location.startswith(("7", "8")):
            region = "southwest"
            factor = 1.02
        else:
            region = "west"
            factor = 1.18

        return {
            "region": region,
            "cost_factor": factor,
            "labor_factor": factor * 1.05,
            "material_factor": factor * 0.95,
        }
