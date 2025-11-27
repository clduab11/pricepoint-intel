"""Natural language query interface implementation."""

import re
from typing import Any

from pricepoint_intel.intelligence_engine.core import IntelligenceEngine
from pricepoint_intel.models.results import QueryResults


class QueryInterface:
    """Natural language query interface.

    Parses natural language queries and translates them
    into structured intelligence queries.
    """

    # Common product patterns
    PRODUCT_PATTERNS = [
        r"(?P<product>laminate\s+flooring)",
        r"(?P<product>hardwood\s+flooring)",
        r"(?P<product>vinyl\s+flooring)",
        r"(?P<product>tile\s+flooring)",
        r"(?P<product>carpet)",
        r"(?P<product>flooring)",
    ]

    # Location patterns (zip codes)
    LOCATION_PATTERNS = [
        r"(?P<location>\d{5}(?:-\d{4})?)",  # ZIP code
        r"in\s+(?P<location>[A-Za-z\s]+,\s*[A-Z]{2})",  # City, State
        r"near\s+(?P<location>[A-Za-z\s]+)",  # "near City"
    ]

    def __init__(self, engine: IntelligenceEngine | None = None) -> None:
        """Initialize the query interface.

        Args:
            engine: Optional IntelligenceEngine instance.
        """
        self._engine = engine or IntelligenceEngine()

    def parse_query(self, query: str) -> dict[str, Any]:
        """Parse a natural language query.

        Args:
            query: Natural language query string.

        Returns:
            Dictionary with parsed query components.
        """
        result = {
            "original_query": query,
            "product": None,
            "location": None,
            "radius_miles": 50,  # Default
            "filters": {},
        }

        query_lower = query.lower()

        # Extract product
        for pattern in self.PRODUCT_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                result["product"] = match.group("product").strip()
                break

        # Extract location
        for pattern in self.LOCATION_PATTERNS:
            match = re.search(pattern, query)
            if match:
                result["location"] = match.group("location").strip()
                break

        # Extract radius if specified
        radius_match = re.search(r"(\d+)\s*(?:mile|mi)", query_lower)
        if radius_match:
            result["radius_miles"] = int(radius_match.group(1))

        # Extract price filters
        price_max_match = re.search(r"under\s*\$?(\d+(?:\.\d+)?)", query_lower)
        if price_max_match:
            result["filters"]["max_price"] = float(price_max_match.group(1))

        price_min_match = re.search(r"over\s*\$?(\d+(?:\.\d+)?)", query_lower)
        if price_min_match:
            result["filters"]["min_price"] = float(price_min_match.group(1))

        return result

    def execute_query(self, query: str) -> QueryResults:
        """Execute a natural language query.

        Args:
            query: Natural language query string.

        Returns:
            QueryResults from the intelligence engine.
        """
        parsed = self.parse_query(query)

        if not parsed["product"]:
            # Try to use the whole query as product
            parsed["product"] = query.split(",")[0].strip()

        if not parsed["location"]:
            # Default location
            parsed["location"] = "35242"

        return self._engine.query(
            product=parsed["product"],
            location=parsed["location"],
            radius_miles=parsed["radius_miles"],
        )

    async def execute_query_async(self, query: str) -> QueryResults:
        """Execute a natural language query asynchronously.

        Args:
            query: Natural language query string.

        Returns:
            QueryResults from the intelligence engine.
        """
        parsed = self.parse_query(query)

        if not parsed["product"]:
            parsed["product"] = query.split(",")[0].strip()

        if not parsed["location"]:
            parsed["location"] = "35242"

        return await self._engine.query_async(
            product=parsed["product"],
            location=parsed["location"],
            radius_miles=parsed["radius_miles"],
        )
