"""Query results model for PricePoint Intel."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VendorResult:
    """Individual vendor pricing result."""

    vendor_id: str
    vendor_name: str
    price_per_unit: float
    unit: str
    distance_miles: float
    last_updated: str
    confidence_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "price_per_unit": self.price_per_unit,
            "unit": self.unit,
            "distance_miles": self.distance_miles,
            "last_updated": self.last_updated,
            "confidence_score": self.confidence_score,
        }


@dataclass
class ProcurementRecord:
    """Public procurement record."""

    record_id: str
    source: str
    entity_name: str
    contract_value: float
    unit_price: float | None
    date: str
    location: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "source": self.source,
            "entity_name": self.entity_name,
            "contract_value": self.contract_value,
            "unit_price": self.unit_price,
            "date": self.date,
            "location": self.location,
        }


@dataclass
class SupplierRelationship:
    """Supplier relationship information."""

    supplier_id: str
    supplier_name: str
    relationship_type: str
    confidence: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class CostBenchmark:
    """Cost benchmarking information."""

    industry_average: float
    geographic_premium: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    unit: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "industry_average": self.industry_average,
            "geographic_premium": self.geographic_premium,
            "percentile_25": self.percentile_25,
            "percentile_50": self.percentile_50,
            "percentile_75": self.percentile_75,
            "unit": self.unit,
        }


@dataclass
class RiskScore:
    """Risk scoring information."""

    supply_chain_stability: float
    price_volatility: float
    availability_risk: float
    overall_score: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "supply_chain_stability": self.supply_chain_stability,
            "price_volatility": self.price_volatility,
            "availability_risk": self.availability_risk,
            "overall_score": self.overall_score,
        }


@dataclass
class QueryResults:
    """Complete query results from the intelligence engine."""

    product: str
    location: str
    radius_miles: int
    vendors: list[VendorResult] = field(default_factory=list)
    procurement_records: list[ProcurementRecord] = field(default_factory=list)
    supplier_relationships: list[SupplierRelationship] = field(default_factory=list)
    benchmark: CostBenchmark | None = None
    risk_score: RiskScore | None = None
    query_time_ms: float = 0.0

    @property
    def vendor_count(self) -> int:
        """Number of vendors found."""
        return len(self.vendors)

    @property
    def price_range(self) -> tuple[float, float] | None:
        """Price range from vendors (min, max)."""
        if not self.vendors:
            return None
        prices = [v.price_per_unit for v in self.vendors]
        return (min(prices), max(prices))

    @property
    def market_average(self) -> float | None:
        """Average price across all vendors."""
        if not self.vendors:
            return None
        return sum(v.price_per_unit for v in self.vendors) / len(self.vendors)

    def summary(self) -> str:
        """Generate a human-readable summary of results."""
        lines = []
        lines.append(f"Query: {self.product}, {self.location}")
        lines.append(f"→ {self.vendor_count} vendors found")

        if self.price_range:
            min_price, max_price = self.price_range
            unit = self.vendors[0].unit if self.vendors else "unit"
            lines.append(f"→ Price range: ${min_price:.2f}-${max_price:.2f}/{unit}")

        if self.market_average:
            lines.append(f"→ Market average: ${self.market_average:.2f}")

        lines.append(f"→ {len(self.procurement_records)} public procurement records")
        lines.append(f"→ {len(self.supplier_relationships)} supplier relationships discovered")

        if self.benchmark:
            lines.append(
                f"→ Industry avg: ${self.benchmark.industry_average:.2f}, "
                f"{self.benchmark.geographic_premium:.1%} geographic premium"
            )

        if self.risk_score:
            lines.append(f"→ Risk score: {self.risk_score.overall_score:.2f}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "product": self.product,
            "location": self.location,
            "radius_miles": self.radius_miles,
            "vendor_count": self.vendor_count,
            "price_range": self.price_range,
            "market_average": self.market_average,
            "vendors": [v.to_dict() for v in self.vendors],
            "procurement_records": [r.to_dict() for r in self.procurement_records],
            "supplier_relationships": [s.to_dict() for s in self.supplier_relationships],
            "benchmark": self.benchmark.to_dict() if self.benchmark else None,
            "risk_score": self.risk_score.to_dict() if self.risk_score else None,
            "query_time_ms": self.query_time_ms,
        }
