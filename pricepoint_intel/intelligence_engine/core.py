"""Core Intelligence Engine implementation."""

import time
from typing import Any

from pricepoint_intel.intelligence_engine.cost_benchmarking.benchmarker import CostBenchmarker
from pricepoint_intel.intelligence_engine.predictive_models.forecaster import PriceForecaster
from pricepoint_intel.intelligence_engine.price_normalization.normalizer import PriceNormalizer
from pricepoint_intel.intelligence_engine.sku_matcher.matcher import SKUMatcher
from pricepoint_intel.intelligence_engine.vendor_discovery.discoverer import VendorDiscoverer
from pricepoint_intel.models.results import (
    CostBenchmark,
    ProcurementRecord,
    QueryResults,
    RiskScore,
    SupplierRelationship,
    VendorResult,
)


class IntelligenceEngine:
    """Main intelligence engine for SKU-level competitive intelligence.

    This engine coordinates multiple data sources and analysis modules
    to provide comprehensive pricing intelligence.

    Example:
        >>> from pricepoint_intel import IntelligenceEngine
        >>> engine = IntelligenceEngine()
        >>> results = engine.query(
        ...     product="laminate flooring",
        ...     location="35242",
        ...     radius_miles=50
        ... )
        >>> print(results.summary())
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the intelligence engine.

        Args:
            config: Optional configuration dictionary for customizing behavior.
        """
        self.config = config or {}
        self._sku_matcher = SKUMatcher()
        self._price_normalizer = PriceNormalizer()
        self._cost_benchmarker = CostBenchmarker()
        self._vendor_discoverer = VendorDiscoverer()
        self._price_forecaster = PriceForecaster()

    def query(
        self,
        product: str,
        location: str,
        radius_miles: int = 50,
        max_vendors: int = 100,
        include_procurement: bool = True,
        include_relationships: bool = True,
        include_benchmarks: bool = True,
        include_risk_scores: bool = True,
    ) -> QueryResults:
        """Execute a comprehensive intelligence query.

        Args:
            product: Product name or description to search for.
            location: Geographic location (zip code or city).
            radius_miles: Search radius in miles.
            max_vendors: Maximum number of vendors to return.
            include_procurement: Include public procurement records.
            include_relationships: Include supplier relationship data.
            include_benchmarks: Include cost benchmarking data.
            include_risk_scores: Include risk scoring data.

        Returns:
            QueryResults object containing all intelligence data.
        """
        start_time = time.time()

        # Initialize results
        results = QueryResults(
            product=product,
            location=location,
            radius_miles=radius_miles,
        )

        # Discover vendors and pricing
        vendors = self._discover_vendors(product, location, radius_miles, max_vendors)
        results.vendors = vendors

        # Normalize prices for geographic and volume factors
        if vendors:
            results.vendors = self._price_normalizer.normalize_prices(
                vendors, location
            )

        # Get public procurement records
        if include_procurement:
            results.procurement_records = self._get_procurement_records(
                product, location, radius_miles
            )

        # Discover supplier relationships
        if include_relationships:
            results.supplier_relationships = self._discover_relationships(
                product, vendors
            )

        # Calculate cost benchmarks
        if include_benchmarks and vendors:
            results.benchmark = self._calculate_benchmarks(vendors, location)

        # Calculate risk scores
        if include_risk_scores and vendors:
            results.risk_score = self._calculate_risk_scores(vendors)

        # Calculate query time
        results.query_time_ms = (time.time() - start_time) * 1000

        return results

    def _discover_vendors(
        self,
        product: str,
        location: str,
        radius_miles: int,
        max_vendors: int,
    ) -> list[VendorResult]:
        """Discover vendors offering the product.

        In production, this would query multiple data sources.
        For now, returns mock data for demonstration.
        """
        return self._vendor_discoverer.discover(
            product=product,
            location=location,
            radius_miles=radius_miles,
            max_results=max_vendors,
        )

    def _get_procurement_records(
        self,
        product: str,
        location: str,
        radius_miles: int,
    ) -> list[ProcurementRecord]:
        """Get public procurement records.

        In production, this would query SAM.gov, state portals, etc.
        For now, returns mock data for demonstration.
        """
        # Mock procurement records
        matched_skus = self._sku_matcher.match(product)
        if not matched_skus:
            return []

        return [
            ProcurementRecord(
                record_id=f"PR-{i:04d}",
                source="SAM.gov" if i % 2 == 0 else "State Procurement Portal",
                entity_name=f"Entity {i}",
                contract_value=50000 + i * 10000,
                unit_price=2.50 + i * 0.10,
                date="2024-01-15",
                location=location,
            )
            for i in range(min(23, len(matched_skus) * 5))
        ]

    def _discover_relationships(
        self,
        product: str,
        vendors: list[VendorResult],
    ) -> list[SupplierRelationship]:
        """Discover supplier relationships.

        In production, this would analyze SEC filings, trade data, etc.
        For now, returns mock data for demonstration.
        """
        if not vendors:
            return []

        relationships = []
        for i, _vendor in enumerate(vendors[:12]):
            relationships.append(
                SupplierRelationship(
                    supplier_id=f"SUP-{i:04d}",
                    supplier_name=f"Supplier {i}",
                    relationship_type="primary" if i < 4 else "secondary",
                    confidence=0.95 - i * 0.03,
                    source="SEC EDGAR" if i % 2 == 0 else "Trade Database",
                )
            )
        return relationships

    def _calculate_benchmarks(
        self,
        vendors: list[VendorResult],
        location: str,
    ) -> CostBenchmark:
        """Calculate cost benchmarks.

        In production, this would use industry data and sophisticated models.
        For now, calculates based on vendor prices.
        """
        return self._cost_benchmarker.calculate(vendors, location)

    def _calculate_risk_scores(
        self,
        vendors: list[VendorResult],
    ) -> RiskScore:
        """Calculate risk scores.

        In production, this would analyze supply chain data, financial health, etc.
        For now, returns mock risk assessment.
        """
        prices = [v.price_per_unit for v in vendors]
        price_volatility = (max(prices) - min(prices)) / (sum(prices) / len(prices))

        return RiskScore(
            supply_chain_stability=0.85,
            price_volatility=price_volatility,
            availability_risk=0.15,
            overall_score=0.80,
        )

    async def query_async(
        self,
        product: str,
        location: str,
        radius_miles: int = 50,
        **kwargs: Any,
    ) -> QueryResults:
        """Async version of query for API use.

        Args:
            product: Product name or description to search for.
            location: Geographic location (zip code or city).
            radius_miles: Search radius in miles.
            **kwargs: Additional arguments passed to query().

        Returns:
            QueryResults object containing all intelligence data.
        """
        # In production, this would use async data sources
        return self.query(product, location, radius_miles, **kwargs)
