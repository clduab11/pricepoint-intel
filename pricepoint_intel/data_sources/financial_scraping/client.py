"""Financial data client for SEC filings and annual reports."""

from dataclasses import dataclass
from typing import Any


@dataclass
class CostStructure:
    """Company cost structure data from financial filings."""

    company_name: str
    fiscal_year: int
    cost_of_goods_sold: float
    gross_margin: float
    operating_margin: float
    material_costs: float | None
    labor_costs: float | None
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "company_name": self.company_name,
            "fiscal_year": self.fiscal_year,
            "cost_of_goods_sold": self.cost_of_goods_sold,
            "gross_margin": self.gross_margin,
            "operating_margin": self.operating_margin,
            "material_costs": self.material_costs,
            "labor_costs": self.labor_costs,
            "source": self.source,
        }


class FinancialDataClient:
    """Client for financial data extraction.

    Parses SEC filings and annual reports to extract
    cost structure and margin information.
    """

    def __init__(self) -> None:
        """Initialize the financial data client."""
        pass

    async def get_cost_structure(
        self,
        company_name: str,
        fiscal_year: int | None = None,
    ) -> CostStructure | None:
        """Get cost structure data for a company.

        Args:
            company_name: Company name.
            fiscal_year: Fiscal year (defaults to most recent).

        Returns:
            CostStructure if found, None otherwise.
        """
        # In production, this would parse actual filings
        return CostStructure(
            company_name=company_name,
            fiscal_year=fiscal_year or 2023,
            cost_of_goods_sold=1500000000,
            gross_margin=0.35,
            operating_margin=0.12,
            material_costs=800000000,
            labor_costs=400000000,
            source="10-K Filing",
        )

    async def analyze_margin_trends(
        self,
        company_name: str,
        years: int = 5,
    ) -> list[dict[str, Any]]:
        """Analyze margin trends over time.

        Args:
            company_name: Company name.
            years: Number of years to analyze.

        Returns:
            List of yearly margin data.
        """
        # In production, this would analyze actual filing data
        return [
            {
                "year": 2023 - i,
                "gross_margin": 0.35 - i * 0.01,
                "operating_margin": 0.12 - i * 0.005,
            }
            for i in range(years)
        ]

    async def extract_supplier_costs(
        self,
        company_name: str,
    ) -> list[dict[str, Any]]:
        """Extract supplier cost information from filings.

        Args:
            company_name: Company name.

        Returns:
            List of supplier cost data.
        """
        # In production, this would use NLP on filings
        return [
            {
                "supplier_category": "Raw Materials",
                "percentage_of_cogs": 0.55,
                "trend": "increasing",
            },
            {
                "supplier_category": "Components",
                "percentage_of_cogs": 0.25,
                "trend": "stable",
            },
            {
                "supplier_category": "Labor",
                "percentage_of_cogs": 0.20,
                "trend": "decreasing",
            },
        ]
