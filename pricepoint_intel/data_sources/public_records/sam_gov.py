"""SAM.gov API client for federal procurement data."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SAMOpportunity:
    """SAM.gov opportunity/contract data."""

    notice_id: str
    title: str
    agency: str
    posted_date: str
    response_deadline: str | None
    naics_code: str | None
    place_of_performance: str | None
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "notice_id": self.notice_id,
            "title": self.title,
            "agency": self.agency,
            "posted_date": self.posted_date,
            "response_deadline": self.response_deadline,
            "naics_code": self.naics_code,
            "place_of_performance": self.place_of_performance,
            "description": self.description,
        }


class SAMGovClient:
    """Client for SAM.gov federal procurement API.

    Provides access to federal contracting opportunities
    and award data.
    """

    BASE_URL = "https://api.sam.gov/opportunities/v2"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the SAM.gov client.

        Args:
            api_key: SAM.gov API key.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key
        self._timeout = timeout

    async def search_opportunities(
        self,
        keywords: str,
        location: str | None = None,
        naics_code: str | None = None,
        max_results: int = 25,
    ) -> list:
        """Search for contracting opportunities.

        Args:
            keywords: Search keywords.
            location: Location filter.
            naics_code: NAICS code filter.
            max_results: Maximum number of results.

        Returns:
            List of ProcurementContract objects.
        """
        # In production, this would call the actual SAM.gov API
        # For now, return mock data
        from pricepoint_intel.data_sources.public_records.client import (
            ProcurementContract,
        )

        return [
            ProcurementContract(
                contract_id=f"SAM-{i:06d}",
                source="SAM.gov",
                entity_name=f"Federal Agency {i}",
                vendor_name=f"Vendor {i}",
                product_description=f"{keywords} - Contract {i}",
                contract_value=100000 + i * 25000,
                unit_price=2.50 + i * 0.05,
                award_date="2024-01-10",
                location=location or "Washington, DC",
            )
            for i in range(min(max_results, 15))
        ]

    async def get_contract_details(
        self,
        contract_id: str,
    ) -> SAMOpportunity | None:
        """Get details for a specific contract.

        Args:
            contract_id: Contract identifier.

        Returns:
            SAMOpportunity if found, None otherwise.
        """
        # In production, this would call the actual SAM.gov API
        return SAMOpportunity(
            notice_id=contract_id,
            title=f"Contract {contract_id}",
            agency="Federal Agency",
            posted_date="2024-01-01",
            response_deadline="2024-02-01",
            naics_code="238330",
            place_of_performance="Washington, DC",
            description="Sample contract description",
        )
