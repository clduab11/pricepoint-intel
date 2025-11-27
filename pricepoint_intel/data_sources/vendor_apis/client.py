"""Vendor API client for direct vendor pricing APIs."""

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class VendorPricingData:
    """Vendor pricing data from API."""

    vendor_id: str
    sku_id: str
    product_name: str
    price: float
    unit: str
    availability: str
    last_updated: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "vendor_id": self.vendor_id,
            "sku_id": self.sku_id,
            "product_name": self.product_name,
            "price": self.price,
            "unit": self.unit,
            "availability": self.availability,
            "last_updated": self.last_updated,
        }


class VendorAPIClient:
    """Client for vendor pricing APIs.

    Integrates with various B2B vendor APIs to fetch
    real-time pricing data.
    """

    def __init__(
        self,
        api_keys: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the vendor API client.

        Args:
            api_keys: Dictionary of vendor_id -> API key mappings.
            timeout: Request timeout in seconds.
        """
        self._api_keys = api_keys or {}
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_pricing(
        self,
        vendor_id: str,
        sku_id: str,
    ) -> VendorPricingData | None:
        """Get pricing for a specific SKU from a vendor.

        Args:
            vendor_id: Vendor identifier.
            sku_id: Product SKU identifier.

        Returns:
            VendorPricingData if found, None otherwise.
        """
        # In production, this would call the actual vendor API
        # For now, return mock data
        return VendorPricingData(
            vendor_id=vendor_id,
            sku_id=sku_id,
            product_name=f"Product {sku_id}",
            price=2.99,
            unit="sqft",
            availability="in_stock",
            last_updated="2024-01-15",
        )

    async def search_products(
        self,
        vendor_id: str,
        query: str,
        max_results: int = 20,
    ) -> list[VendorPricingData]:
        """Search for products from a vendor.

        Args:
            vendor_id: Vendor identifier.
            query: Product search query.
            max_results: Maximum number of results.

        Returns:
            List of VendorPricingData objects.
        """
        # In production, this would call the actual vendor API
        # For now, return mock data
        return [
            VendorPricingData(
                vendor_id=vendor_id,
                sku_id=f"SKU-{i:04d}",
                product_name=f"{query} Product {i}",
                price=2.50 + i * 0.10,
                unit="sqft",
                availability="in_stock",
                last_updated="2024-01-15",
            )
            for i in range(min(max_results, 10))
        ]

    def add_api_key(self, vendor_id: str, api_key: str) -> None:
        """Add or update an API key for a vendor.

        Args:
            vendor_id: Vendor identifier.
            api_key: API key for the vendor.
        """
        self._api_keys[vendor_id] = api_key

    def get_supported_vendors(self) -> list[str]:
        """Get list of vendors with configured API keys.

        Returns:
            List of vendor identifiers.
        """
        return list(self._api_keys.keys())
