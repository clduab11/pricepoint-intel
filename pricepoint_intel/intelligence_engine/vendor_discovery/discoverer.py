"""Vendor discovery algorithm implementation."""

import random
from datetime import datetime, timedelta

from pricepoint_intel.models.results import VendorResult


class VendorDiscoverer:
    """Vendor discovery for finding suppliers in a geographic area.

    Discovers vendors offering specific products within a defined
    geographic radius.
    """

    # Sample vendor database for demonstration
    SAMPLE_VENDORS = [
        {"id": "V001", "name": "Floor & Decor", "type": "big_box"},
        {"id": "V002", "name": "HD Supply", "type": "distributor"},
        {"id": "V003", "name": "ABC Supply", "type": "distributor"},
        {"id": "V004", "name": "Ferguson Enterprises", "type": "distributor"},
        {"id": "V005", "name": "Lowe's Pro Supply", "type": "big_box"},
        {"id": "V006", "name": "BuildDirect", "type": "online"},
        {"id": "V007", "name": "Lumber Liquidators", "type": "specialty"},
        {"id": "V008", "name": "ProSource Wholesale", "type": "wholesale"},
        {"id": "V009", "name": "Shaw Direct", "type": "manufacturer"},
        {"id": "V010", "name": "Mohawk Industries", "type": "manufacturer"},
        {"id": "V011", "name": "Armstrong Flooring", "type": "manufacturer"},
        {"id": "V012", "name": "Tarkett", "type": "manufacturer"},
        {"id": "V013", "name": "Interface", "type": "manufacturer"},
        {"id": "V014", "name": "Mannington", "type": "manufacturer"},
        {"id": "V015", "name": "Pergo", "type": "manufacturer"},
        {"id": "V016", "name": "Quick-Step", "type": "manufacturer"},
        {"id": "V017", "name": "COREtec", "type": "manufacturer"},
        {"id": "V018", "name": "Karndean", "type": "manufacturer"},
        {"id": "V019", "name": "LL Flooring", "type": "specialty"},
        {"id": "V020", "name": "The Home Depot Pro", "type": "big_box"},
        {"id": "V021", "name": "Menards Pro", "type": "big_box"},
        {"id": "V022", "name": "Builders FirstSource", "type": "distributor"},
        {"id": "V023", "name": "US LBM Holdings", "type": "distributor"},
        {"id": "V024", "name": "84 Lumber", "type": "distributor"},
        {"id": "V025", "name": "BlueLinx Holdings", "type": "distributor"},
        {"id": "V026", "name": "Beacon Roofing Supply", "type": "distributor"},
        {"id": "V027", "name": "BMC Stock Holdings", "type": "distributor"},
        {"id": "V028", "name": "Patrick Industries", "type": "manufacturer"},
        {"id": "V029", "name": "Masco Corporation", "type": "manufacturer"},
        {"id": "V030", "name": "Owens Corning", "type": "manufacturer"},
        {"id": "V031", "name": "Local Flooring Co", "type": "local"},
        {"id": "V032", "name": "Regional Tile & Stone", "type": "local"},
        {"id": "V033", "name": "Metro Flooring Solutions", "type": "local"},
        {"id": "V034", "name": "Premier Floor Covering", "type": "local"},
        {"id": "V035", "name": "City Flooring Center", "type": "local"},
        {"id": "V036", "name": "Commercial Flooring Inc", "type": "commercial"},
        {"id": "V037", "name": "Industrial Floor Systems", "type": "commercial"},
        {"id": "V038", "name": "Contract Flooring Supply", "type": "commercial"},
        {"id": "V039", "name": "Wholesale Flooring Depot", "type": "wholesale"},
        {"id": "V040", "name": "Budget Floors Direct", "type": "discount"},
        {"id": "V041", "name": "Express Flooring", "type": "discount"},
        {"id": "V042", "name": "National Floors Direct", "type": "discount"},
        {"id": "V043", "name": "Empire Today", "type": "national"},
        {"id": "V044", "name": "Carpeteria", "type": "specialty"},
        {"id": "V045", "name": "Abbey Carpet & Floor", "type": "specialty"},
        {"id": "V046", "name": "CarpetOne Floor & Home", "type": "specialty"},
        {"id": "V047", "name": "Flooring America", "type": "specialty"},
    ]

    def __init__(self, seed: int | None = None) -> None:
        """Initialize the vendor discoverer.

        Args:
            seed: Random seed for reproducible results (for testing).
        """
        if seed is not None:
            random.seed(seed)
        self._vendors = self.SAMPLE_VENDORS.copy()

    def discover(
        self,
        product: str,
        location: str,
        radius_miles: int = 50,
        max_results: int = 50,
        vendor_types: list[str] | None = None,
    ) -> list[VendorResult]:
        """Discover vendors offering a product in a geographic area.

        Args:
            product: Product to search for.
            location: Center location for search (zip code).
            radius_miles: Search radius in miles.
            max_results: Maximum number of vendors to return.
            vendor_types: Optional filter for vendor types.

        Returns:
            List of VendorResult objects.
        """
        # Filter vendors by type if specified
        candidates = self._vendors
        if vendor_types:
            candidates = [v for v in candidates if v["type"] in vendor_types]

        # Limit to max_results
        selected = candidates[:max_results]

        # Generate vendor results with realistic pricing
        results = []
        base_price = self._get_base_price(product)

        for _i, vendor in enumerate(selected):
            # Generate distance within radius
            distance = random.uniform(1, min(radius_miles, 50))

            # Generate price with variation
            price_variation = random.uniform(0.85, 1.35)
            price = round(base_price * price_variation, 2)

            # Generate last updated date (within last 30 days)
            days_ago = random.randint(0, 30)
            last_updated = (datetime.now() - timedelta(days=days_ago)).strftime(
                "%Y-%m-%d"
            )

            # Confidence score based on data freshness and vendor type
            confidence = 0.95 - (days_ago / 100) - (random.random() * 0.1)

            results.append(
                VendorResult(
                    vendor_id=vendor["id"],
                    vendor_name=vendor["name"],
                    price_per_unit=price,
                    unit=self._get_unit(product),
                    distance_miles=round(distance, 1),
                    last_updated=last_updated,
                    confidence_score=max(0.5, min(1.0, confidence)),
                )
            )

        # Sort by price
        results.sort(key=lambda x: x.price_per_unit)

        return results

    def _get_base_price(self, product: str) -> float:
        """Get base price for a product type.

        Args:
            product: Product description.

        Returns:
            Base price per unit.
        """
        product_lower = product.lower()

        if "laminate" in product_lower:
            return 2.50
        elif "hardwood" in product_lower:
            return 5.00
        elif "vinyl" in product_lower:
            return 3.00
        elif "tile" in product_lower:
            return 4.00
        elif "carpet" in product_lower:
            return 2.00
        else:
            return 3.00

    def _get_unit(self, product: str) -> str:
        """Get unit of measure for a product type.

        Args:
            product: Product description.

        Returns:
            Unit of measure (e.g., "sqft").
        """
        product_lower = product.lower()

        if any(x in product_lower for x in ["flooring", "tile", "carpet", "vinyl"]):
            return "sqft"
        elif "board" in product_lower:
            return "board"
        elif "roll" in product_lower:
            return "roll"
        else:
            return "unit"

    def get_vendor_by_id(self, vendor_id: str) -> dict | None:
        """Get vendor details by ID.

        Args:
            vendor_id: Vendor identifier.

        Returns:
            Vendor dictionary or None if not found.
        """
        for vendor in self._vendors:
            if vendor["id"] == vendor_id:
                return vendor
        return None

    def get_vendor_types(self) -> list[str]:
        """Get list of available vendor types.

        Returns:
            List of vendor type strings.
        """
        return list({v["type"] for v in self._vendors})
