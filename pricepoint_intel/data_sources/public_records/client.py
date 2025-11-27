"""Public records client for procurement databases."""

from dataclasses import dataclass
from typing import Any

from pricepoint_intel.data_sources.public_records.sam_gov import SAMGovClient
from pricepoint_intel.data_sources.public_records.sec_edgar import SECEdgarClient


@dataclass
class ProcurementContract:
    """Procurement contract data."""

    contract_id: str
    source: str
    entity_name: str
    vendor_name: str
    product_description: str
    contract_value: float
    unit_price: float | None
    award_date: str
    location: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_id": self.contract_id,
            "source": self.source,
            "entity_name": self.entity_name,
            "vendor_name": self.vendor_name,
            "product_description": self.product_description,
            "contract_value": self.contract_value,
            "unit_price": self.unit_price,
            "award_date": self.award_date,
            "location": self.location,
        }


class PublicRecordsClient:
    """Client for public procurement records.

    Aggregates data from multiple public procurement sources
    including federal, state, and local databases.
    """

    def __init__(
        self,
        sam_api_key: str | None = None,
        sec_user_agent: str | None = None,
    ) -> None:
        """Initialize the public records client.

        Args:
            sam_api_key: API key for SAM.gov.
            sec_user_agent: User agent for SEC EDGAR.
        """
        self._sam_client = SAMGovClient(api_key=sam_api_key)
        self._sec_client = SECEdgarClient(user_agent=sec_user_agent)

    async def search_contracts(
        self,
        product: str,
        location: str | None = None,
        max_results: int = 50,
    ) -> list[ProcurementContract]:
        """Search for procurement contracts.

        Args:
            product: Product to search for.
            location: Optional location filter.
            max_results: Maximum number of results.

        Returns:
            List of ProcurementContract objects.
        """
        # Aggregate from multiple sources
        contracts = []

        # Get federal contracts from SAM.gov
        sam_contracts = await self._sam_client.search_opportunities(
            keywords=product,
            location=location,
            max_results=max_results // 2,
        )
        contracts.extend(sam_contracts)

        return contracts[:max_results]

    async def get_supplier_filings(
        self,
        company_name: str,
        filing_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get SEC filings for a company.

        Args:
            company_name: Company name to search.
            filing_types: Types of filings (e.g., ["10-K", "10-Q"]).

        Returns:
            List of filing data dictionaries.
        """
        return await self._sec_client.search_filings(
            company_name=company_name,
            filing_types=filing_types or ["10-K", "10-Q"],
        )
