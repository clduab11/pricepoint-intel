"""SKU Matching algorithm implementation."""

from dataclasses import dataclass
from typing import Any

from fuzzywuzzy import fuzz


@dataclass
class SKUMatch:
    """Result of a SKU matching operation."""

    sku_id: str
    product_name: str
    match_score: float
    source: str
    category: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sku_id": self.sku_id,
            "product_name": self.product_name,
            "match_score": self.match_score,
            "source": self.source,
            "category": self.category,
        }


class SKUMatcher:
    """SKU matching algorithm for product identification across sources.

    Uses fuzzy string matching and category-based filtering to identify
    products across different vendor catalogs and data sources.
    """

    # Sample product catalog for demonstration
    SAMPLE_CATALOG = [
        {
            "sku_id": "LAM-FLOOR-001",
            "product_name": "Pergo TimberCraft Laminate Flooring",
            "category": "flooring",
            "subcategory": "laminate",
        },
        {
            "sku_id": "LAM-FLOOR-002",
            "product_name": "Shaw Repel Laminate Flooring",
            "category": "flooring",
            "subcategory": "laminate",
        },
        {
            "sku_id": "LAM-FLOOR-003",
            "product_name": "Mohawk RevWood Plus Laminate",
            "category": "flooring",
            "subcategory": "laminate",
        },
        {
            "sku_id": "HWD-FLOOR-001",
            "product_name": "Bruce Hardwood Flooring Oak",
            "category": "flooring",
            "subcategory": "hardwood",
        },
        {
            "sku_id": "VNL-FLOOR-001",
            "product_name": "LifeProof Luxury Vinyl Plank",
            "category": "flooring",
            "subcategory": "vinyl",
        },
        {
            "sku_id": "TIL-FLOOR-001",
            "product_name": "TrafficMaster Ceramic Tile",
            "category": "flooring",
            "subcategory": "tile",
        },
    ]

    def __init__(self, min_match_score: float = 60.0) -> None:
        """Initialize the SKU matcher.

        Args:
            min_match_score: Minimum fuzzy match score (0-100) to consider a match.
        """
        self.min_match_score = min_match_score
        self._catalog = self.SAMPLE_CATALOG.copy()

    def match(
        self,
        query: str,
        category: str | None = None,
        max_results: int = 10,
    ) -> list[SKUMatch]:
        """Find matching SKUs for a product query.

        Args:
            query: Product search query.
            category: Optional category filter.
            max_results: Maximum number of results to return.

        Returns:
            List of SKUMatch objects sorted by match score.
        """
        matches = []

        for product in self._catalog:
            # Filter by category if specified
            if category and product["category"].lower() != category.lower():
                continue

            # Calculate fuzzy match score
            product_name = product["product_name"]
            score = max(
                fuzz.token_set_ratio(query.lower(), product_name.lower()),
                fuzz.partial_ratio(query.lower(), product_name.lower()),
            )

            if score >= self.min_match_score:
                matches.append(
                    SKUMatch(
                        sku_id=product["sku_id"],
                        product_name=product["product_name"],
                        match_score=score / 100.0,
                        source="internal_catalog",
                        category=product["category"],
                    )
                )

        # Sort by match score descending
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return matches[:max_results]

    def match_across_sources(
        self,
        query: str,
        sources: list[str] | None = None,
    ) -> list[SKUMatch]:
        """Match SKUs across multiple data sources.

        Args:
            query: Product search query.
            sources: Optional list of sources to search.

        Returns:
            List of SKUMatch objects from all sources.
        """
        # In production, this would query multiple vendor APIs
        # For now, use the internal catalog
        return self.match(query)

    def add_to_catalog(self, product: dict[str, Any]) -> None:
        """Add a product to the internal catalog.

        Args:
            product: Product dictionary with sku_id, product_name, category.
        """
        required_fields = ["sku_id", "product_name", "category"]
        if not all(field in product for field in required_fields):
            raise ValueError(f"Product must have fields: {required_fields}")
        self._catalog.append(product)

    def get_catalog_size(self) -> int:
        """Get the number of products in the catalog."""
        return len(self._catalog)
