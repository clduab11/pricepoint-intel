"""Geospatial risk framework for vendor analysis and pricing intelligence.

Provides distance-based vendor analysis, regional pricing variance detection,
and cost benchmarking aggregation by market region.
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import logging

from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session

from pricepoint_intel.database.models import (
    Vendor,
    VendorPricing,
    GeographicMarket,
    DistributionCenter,
    SKU,
    PriceHistory,
)
from pricepoint_intel.database.connection import session_scope, DatabaseConfig

logger = logging.getLogger(__name__)

# Earth's radius in miles for Haversine formula
EARTH_RADIUS_MILES = 3958.8


class RiskLevel(str, Enum):
    """Risk level classifications."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of pricing anomalies."""

    PRICE_SPIKE = "price_spike"
    PRICE_DROP = "price_drop"
    REGIONAL_OUTLIER = "regional_outlier"
    VENDOR_OUTLIER = "vendor_outlier"
    TEMPORAL_ANOMALY = "temporal_anomaly"


@dataclass
class VendorProximityResult:
    """Result of vendor proximity analysis."""

    vendor_id: str
    vendor_name: str
    distance_miles: float
    proximity_score: float  # 0-1, higher is closer
    latitude: float
    longitude: float
    reliability_score: Optional[float] = None
    avg_lead_time_days: Optional[int] = None
    composite_score: float = 0.0  # Combined proximity + reliability

    def to_dict(self) -> dict:
        return {
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "distance_miles": round(self.distance_miles, 2),
            "proximity_score": round(self.proximity_score, 3),
            "coordinates": {"latitude": self.latitude, "longitude": self.longitude},
            "reliability_score": self.reliability_score,
            "avg_lead_time_days": self.avg_lead_time_days,
            "composite_score": round(self.composite_score, 3),
        }


@dataclass
class PricingVarianceResult:
    """Result of pricing variance analysis."""

    sku_id: str
    product_name: str
    region: str
    price: float
    regional_mean: float
    regional_std: float
    z_score: float
    is_anomaly: bool
    anomaly_type: Optional[AnomalyType] = None
    variance_pct: float = 0.0
    vendor_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sku_id": self.sku_id,
            "product_name": self.product_name,
            "region": self.region,
            "price": round(self.price, 2),
            "regional_mean": round(self.regional_mean, 2),
            "regional_std": round(self.regional_std, 2),
            "z_score": round(self.z_score, 2),
            "variance_pct": round(self.variance_pct, 2),
            "is_anomaly": self.is_anomaly,
            "anomaly_type": self.anomaly_type.value if self.anomaly_type else None,
            "vendor_id": self.vendor_id,
        }


@dataclass
class RegionalBenchmark:
    """Regional pricing benchmark data."""

    region: str
    market_id: Optional[str] = None
    sku_count: int = 0
    vendor_count: int = 0
    price_mean: float = 0.0
    price_median: float = 0.0
    price_min: float = 0.0
    price_max: float = 0.0
    price_std: float = 0.0
    percentile_25: float = 0.0
    percentile_75: float = 0.0
    cost_index: float = 1.0
    sample_size: int = 0

    def to_dict(self) -> dict:
        return {
            "region": self.region,
            "market_id": self.market_id,
            "sku_count": self.sku_count,
            "vendor_count": self.vendor_count,
            "pricing": {
                "mean": round(self.price_mean, 2),
                "median": round(self.price_median, 2),
                "min": round(self.price_min, 2),
                "max": round(self.price_max, 2),
                "std": round(self.price_std, 2),
                "percentile_25": round(self.percentile_25, 2),
                "percentile_75": round(self.percentile_75, 2),
            },
            "cost_index": round(self.cost_index, 3),
            "sample_size": self.sample_size,
        }


@dataclass
class RiskAssessment:
    """Overall risk assessment for a vendor or region."""

    entity_id: str
    entity_type: str  # "vendor" or "region"
    risk_level: RiskLevel
    risk_score: float  # 0-100
    factors: dict = field(default_factory=dict)
    recommendations: list = field(default_factory=list)
    assessed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "risk_level": self.risk_level.value,
            "risk_score": round(self.risk_score, 1),
            "factors": self.factors,
            "recommendations": self.recommendations,
            "assessed_at": self.assessed_at.isoformat(),
        }


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate the great-circle distance between two points on Earth.

    Args:
        lat1: Latitude of point 1 (degrees)
        lon1: Longitude of point 1 (degrees)
        lat2: Latitude of point 2 (degrees)
        lon2: Longitude of point 2 (degrees)

    Returns:
        Distance in miles
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_MILES * c


class ProximityScorer:
    """Calculate proximity scores for vendors relative to distribution centers."""

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
        max_distance_miles: float = 500.0,
        decay_rate: float = 0.01,
    ):
        """Initialize proximity scorer.

        Args:
            db_config: Database configuration
            max_distance_miles: Maximum distance for scoring (vendors beyond this get 0)
            decay_rate: Exponential decay rate for distance scoring
        """
        self.db_config = db_config
        self.max_distance = max_distance_miles
        self.decay_rate = decay_rate

    def calculate_proximity_score(self, distance_miles: float) -> float:
        """Calculate proximity score from distance.

        Uses exponential decay: score = e^(-decay_rate * distance)
        Capped at max_distance where score becomes 0.

        Args:
            distance_miles: Distance in miles

        Returns:
            Proximity score between 0 and 1
        """
        if distance_miles >= self.max_distance:
            return 0.0

        score = math.exp(-self.decay_rate * distance_miles)
        return max(0.0, min(1.0, score))

    def score_vendors_from_point(
        self,
        latitude: float,
        longitude: float,
        limit: int = 50,
        min_reliability: Optional[float] = None,
    ) -> list[VendorProximityResult]:
        """Score all vendors by proximity to a given point.

        Args:
            latitude: Target latitude
            longitude: Target longitude
            limit: Maximum vendors to return
            min_reliability: Minimum reliability score filter

        Returns:
            List of VendorProximityResult sorted by composite score
        """
        results = []

        with session_scope(self.db_config) as session:
            query = session.query(Vendor).filter(
                Vendor.is_active == True,
                Vendor.latitude.isnot(None),
                Vendor.longitude.isnot(None),
            )

            if min_reliability is not None:
                query = query.filter(
                    Vendor.reliability_score >= min_reliability
                )

            vendors = query.all()

            for vendor in vendors:
                distance = haversine_distance(
                    latitude, longitude,
                    vendor.latitude, vendor.longitude
                )

                if distance > self.max_distance:
                    continue

                proximity_score = self.calculate_proximity_score(distance)

                # Calculate composite score (weighted average)
                reliability = vendor.reliability_score or 0.5
                composite = (proximity_score * 0.6) + (reliability * 0.4)

                results.append(
                    VendorProximityResult(
                        vendor_id=vendor.vendor_id,
                        vendor_name=vendor.vendor_name,
                        distance_miles=distance,
                        proximity_score=proximity_score,
                        latitude=vendor.latitude,
                        longitude=vendor.longitude,
                        reliability_score=vendor.reliability_score,
                        avg_lead_time_days=vendor.avg_lead_time_days,
                        composite_score=composite,
                    )
                )

        # Sort by composite score (highest first)
        results.sort(key=lambda x: x.composite_score, reverse=True)
        return results[:limit]

    def score_vendors_for_market(
        self,
        market_id: str,
        limit: int = 50,
    ) -> list[VendorProximityResult]:
        """Score vendors by proximity to a market's centroid.

        Args:
            market_id: Geographic market identifier
            limit: Maximum vendors to return

        Returns:
            List of VendorProximityResult sorted by composite score
        """
        with session_scope(self.db_config) as session:
            market = (
                session.query(GeographicMarket)
                .filter(GeographicMarket.market_id == market_id)
                .first()
            )

            if not market:
                logger.warning(f"Market not found: {market_id}")
                return []

            return self.score_vendors_from_point(
                market.latitude,
                market.longitude,
                limit=limit,
            )

    def find_nearest_distribution_centers(
        self,
        latitude: float,
        longitude: float,
        limit: int = 5,
    ) -> list[dict]:
        """Find nearest distribution centers to a point.

        Args:
            latitude: Target latitude
            longitude: Target longitude
            limit: Maximum centers to return

        Returns:
            List of distribution center info with distances
        """
        results = []

        with session_scope(self.db_config) as session:
            centers = (
                session.query(DistributionCenter)
                .filter(DistributionCenter.is_active == True)
                .all()
            )

            for center in centers:
                distance = haversine_distance(
                    latitude, longitude,
                    center.latitude, center.longitude
                )

                results.append({
                    "center_id": center.center_id,
                    "center_name": center.center_name,
                    "center_type": center.center_type,
                    "distance_miles": round(distance, 2),
                    "city": center.city,
                    "state": center.state,
                    "service_radius_miles": center.service_radius_miles,
                    "within_service_area": (
                        center.service_radius_miles
                        and distance <= center.service_radius_miles
                    ),
                })

        results.sort(key=lambda x: x["distance_miles"])
        return results[:limit]


class VarianceDetector:
    """Detect pricing variance and anomalies across regions and vendors."""

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
        z_score_threshold: float = 2.0,
        min_samples: int = 3,
    ):
        """Initialize variance detector.

        Args:
            db_config: Database configuration
            z_score_threshold: Z-score threshold for anomaly detection
            min_samples: Minimum samples required for variance calculation
        """
        self.db_config = db_config
        self.z_threshold = z_score_threshold
        self.min_samples = min_samples

    def detect_regional_anomalies(
        self,
        sku_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[PricingVarianceResult]:
        """Detect pricing anomalies by comparing against regional averages.

        Args:
            sku_id: Optional SKU filter
            category: Optional category filter

        Returns:
            List of PricingVarianceResult for detected anomalies
        """
        results = []

        with session_scope(self.db_config) as session:
            # Build base query
            query = (
                session.query(
                    VendorPricing.sku_id,
                    VendorPricing.vendor_id,
                    VendorPricing.price,
                    VendorPricing.geographic_region,
                    SKU.product_name,
                )
                .join(SKU, VendorPricing.sku_id == SKU.sku_id)
                .filter(VendorPricing.geographic_region.isnot(None))
            )

            if sku_id:
                query = query.filter(VendorPricing.sku_id == sku_id)
            if category:
                query = query.filter(SKU.category == category)

            pricing_data = query.all()

            # Group by region and SKU
            regional_data: dict[tuple[str, str], list] = {}
            for row in pricing_data:
                key = (row.geographic_region, row.sku_id)
                if key not in regional_data:
                    regional_data[key] = []
                regional_data[key].append({
                    "price": float(row.price),
                    "vendor_id": row.vendor_id,
                    "product_name": row.product_name,
                })

            # Calculate variance for each region/SKU combination
            for (region, sku), prices in regional_data.items():
                if len(prices) < self.min_samples:
                    continue

                price_values = [p["price"] for p in prices]
                mean = statistics.mean(price_values)
                std = statistics.stdev(price_values) if len(price_values) > 1 else 0

                if std == 0:
                    continue

                for p in prices:
                    z_score = (p["price"] - mean) / std
                    is_anomaly = abs(z_score) > self.z_threshold
                    variance_pct = ((p["price"] - mean) / mean) * 100

                    if is_anomaly:
                        anomaly_type = (
                            AnomalyType.PRICE_SPIKE if z_score > 0
                            else AnomalyType.PRICE_DROP
                        )

                        results.append(
                            PricingVarianceResult(
                                sku_id=sku,
                                product_name=p["product_name"],
                                region=region,
                                price=p["price"],
                                regional_mean=mean,
                                regional_std=std,
                                z_score=z_score,
                                is_anomaly=True,
                                anomaly_type=anomaly_type,
                                variance_pct=variance_pct,
                                vendor_id=p["vendor_id"],
                            )
                        )

        # Sort by absolute z-score (most anomalous first)
        results.sort(key=lambda x: abs(x.z_score), reverse=True)
        return results

    def detect_vendor_outliers(
        self,
        vendor_id: str,
    ) -> list[PricingVarianceResult]:
        """Detect if a vendor's prices are outliers compared to market.

        Args:
            vendor_id: Vendor to analyze

        Returns:
            List of PricingVarianceResult for outlier prices
        """
        results = []

        with session_scope(self.db_config) as session:
            # Get vendor's prices
            vendor_prices = (
                session.query(
                    VendorPricing.sku_id,
                    VendorPricing.price,
                    VendorPricing.geographic_region,
                    SKU.product_name,
                )
                .join(SKU, VendorPricing.sku_id == SKU.sku_id)
                .filter(VendorPricing.vendor_id == vendor_id)
                .all()
            )

            for vp in vendor_prices:
                # Get all prices for this SKU in the same region
                all_prices = (
                    session.query(VendorPricing.price)
                    .filter(
                        VendorPricing.sku_id == vp.sku_id,
                        VendorPricing.geographic_region == vp.geographic_region,
                    )
                    .all()
                )

                prices = [float(p[0]) for p in all_prices]

                if len(prices) < self.min_samples:
                    continue

                mean = statistics.mean(prices)
                std = statistics.stdev(prices) if len(prices) > 1 else 0

                if std == 0:
                    continue

                vendor_price = float(vp.price)
                z_score = (vendor_price - mean) / std

                if abs(z_score) > self.z_threshold:
                    results.append(
                        PricingVarianceResult(
                            sku_id=vp.sku_id,
                            product_name=vp.product_name,
                            region=vp.geographic_region or "all",
                            price=vendor_price,
                            regional_mean=mean,
                            regional_std=std,
                            z_score=z_score,
                            is_anomaly=True,
                            anomaly_type=AnomalyType.VENDOR_OUTLIER,
                            variance_pct=((vendor_price - mean) / mean) * 100,
                            vendor_id=vendor_id,
                        )
                    )

        return results

    def get_price_volatility(
        self,
        sku_id: str,
        vendor_id: Optional[str] = None,
        days: int = 30,
    ) -> dict:
        """Calculate price volatility for a SKU over time.

        Args:
            sku_id: SKU identifier
            vendor_id: Optional vendor filter
            days: Number of days to analyze

        Returns:
            Dictionary with volatility metrics
        """
        with session_scope(self.db_config) as session:
            cutoff = datetime.utcnow()
            # Note: In production, use proper date arithmetic

            query = (
                session.query(PriceHistory.price, PriceHistory.recorded_at)
                .filter(PriceHistory.sku_id == sku_id)
                .order_by(PriceHistory.recorded_at.desc())
            )

            if vendor_id:
                query = query.filter(PriceHistory.vendor_id == vendor_id)

            history = query.limit(days).all()

            if len(history) < 2:
                return {
                    "sku_id": sku_id,
                    "data_points": len(history),
                    "volatility": None,
                    "message": "Insufficient data",
                }

            prices = [float(h[0]) for h in history]
            mean = statistics.mean(prices)
            std = statistics.stdev(prices)

            # Calculate coefficient of variation
            cv = (std / mean) * 100 if mean > 0 else 0

            # Calculate daily returns for volatility
            returns = []
            for i in range(1, len(prices)):
                if prices[i - 1] > 0:
                    returns.append((prices[i] - prices[i - 1]) / prices[i - 1])

            return_volatility = statistics.stdev(returns) * 100 if len(returns) > 1 else 0

            return {
                "sku_id": sku_id,
                "vendor_id": vendor_id,
                "data_points": len(history),
                "price_mean": round(mean, 2),
                "price_std": round(std, 2),
                "coefficient_of_variation": round(cv, 2),
                "return_volatility_pct": round(return_volatility, 2),
                "price_min": round(min(prices), 2),
                "price_max": round(max(prices), 2),
                "volatility_level": (
                    "low" if cv < 5 else "moderate" if cv < 15 else "high"
                ),
            }


class RegionalBenchmarker:
    """Aggregate cost benchmarking by market region."""

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
    ):
        """Initialize regional benchmarker.

        Args:
            db_config: Database configuration
        """
        self.db_config = db_config

    def calculate_benchmark(
        self,
        region: Optional[str] = None,
        category: Optional[str] = None,
    ) -> RegionalBenchmark:
        """Calculate pricing benchmarks for a region.

        Args:
            region: Geographic region filter
            category: Product category filter

        Returns:
            RegionalBenchmark with aggregated statistics
        """
        with session_scope(self.db_config) as session:
            query = (
                session.query(VendorPricing.price, VendorPricing.vendor_id)
                .join(SKU, VendorPricing.sku_id == SKU.sku_id)
            )

            if region:
                query = query.filter(VendorPricing.geographic_region == region)
            if category:
                query = query.filter(SKU.category == category)

            results = query.all()

            if not results:
                return RegionalBenchmark(
                    region=region or "all",
                    sample_size=0,
                )

            prices = [float(r[0]) for r in results]
            vendors = set(r[1] for r in results)

            # Calculate percentiles
            sorted_prices = sorted(prices)
            n = len(sorted_prices)

            def percentile(data: list, p: float) -> float:
                k = (len(data) - 1) * p / 100
                f = math.floor(k)
                c = math.ceil(k)
                if f == c:
                    return data[int(k)]
                return data[f] * (c - k) + data[c] * (k - f)

            # Get cost index from market table
            cost_index = 1.0
            if region:
                market = (
                    session.query(GeographicMarket)
                    .filter(GeographicMarket.region_name == region)
                    .first()
                )
                if market:
                    cost_index = market.cost_of_living_index

            # Count unique SKUs
            sku_count_query = (
                session.query(func.count(func.distinct(VendorPricing.sku_id)))
                .join(SKU, VendorPricing.sku_id == SKU.sku_id)
            )
            if region:
                sku_count_query = sku_count_query.filter(
                    VendorPricing.geographic_region == region
                )
            if category:
                sku_count_query = sku_count_query.filter(SKU.category == category)

            sku_count = sku_count_query.scalar() or 0

            return RegionalBenchmark(
                region=region or "all",
                sku_count=sku_count,
                vendor_count=len(vendors),
                price_mean=statistics.mean(prices),
                price_median=statistics.median(prices),
                price_min=min(prices),
                price_max=max(prices),
                price_std=statistics.stdev(prices) if len(prices) > 1 else 0,
                percentile_25=percentile(sorted_prices, 25),
                percentile_75=percentile(sorted_prices, 75),
                cost_index=cost_index,
                sample_size=n,
            )

    def compare_regions(
        self,
        regions: list[str],
        category: Optional[str] = None,
    ) -> list[RegionalBenchmark]:
        """Compare benchmarks across multiple regions.

        Args:
            regions: List of region names to compare
            category: Optional product category filter

        Returns:
            List of RegionalBenchmark for each region
        """
        return [
            self.calculate_benchmark(region=r, category=category)
            for r in regions
        ]

    def get_category_benchmarks(
        self,
        region: Optional[str] = None,
    ) -> dict[str, RegionalBenchmark]:
        """Get benchmarks broken down by category.

        Args:
            region: Optional region filter

        Returns:
            Dictionary of benchmarks by category
        """
        categories = [
            "flooring", "building_materials", "electrical", "plumbing",
            "hvac", "hardware", "lumber", "paint", "tools", "other"
        ]

        return {
            cat: self.calculate_benchmark(region=region, category=cat)
            for cat in categories
        }


class GeospatialRiskAnalyzer:
    """Main orchestrator for geospatial risk analysis."""

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
    ):
        """Initialize risk analyzer.

        Args:
            db_config: Database configuration
        """
        self.db_config = db_config
        self.proximity_scorer = ProximityScorer(db_config)
        self.variance_detector = VarianceDetector(db_config)
        self.benchmarker = RegionalBenchmarker(db_config)

    def assess_vendor_risk(
        self,
        vendor_id: str,
        reference_lat: Optional[float] = None,
        reference_lon: Optional[float] = None,
    ) -> RiskAssessment:
        """Perform comprehensive risk assessment for a vendor.

        Args:
            vendor_id: Vendor to assess
            reference_lat: Optional reference latitude for distance scoring
            reference_lon: Optional reference longitude for distance scoring

        Returns:
            RiskAssessment with risk score and recommendations
        """
        factors = {}
        recommendations = []
        risk_score = 0.0

        with session_scope(self.db_config) as session:
            vendor = (
                session.query(Vendor)
                .filter(Vendor.vendor_id == vendor_id)
                .first()
            )

            if not vendor:
                return RiskAssessment(
                    entity_id=vendor_id,
                    entity_type="vendor",
                    risk_level=RiskLevel.CRITICAL,
                    risk_score=100.0,
                    factors={"error": "Vendor not found"},
                    recommendations=["Verify vendor exists in system"],
                )

            # Factor 1: Reliability score
            if vendor.reliability_score:
                reliability_risk = (1 - vendor.reliability_score) * 30
                factors["reliability"] = {
                    "score": vendor.reliability_score,
                    "risk_contribution": reliability_risk,
                }
                risk_score += reliability_risk

                if vendor.reliability_score < 0.7:
                    recommendations.append(
                        "Review vendor reliability - score below 70%"
                    )
            else:
                factors["reliability"] = {
                    "score": None,
                    "risk_contribution": 15,
                }
                risk_score += 15
                recommendations.append("No reliability data - consider vendor review")

            # Factor 2: Lead time
            if vendor.avg_lead_time_days:
                if vendor.avg_lead_time_days > 14:
                    lead_time_risk = min(20, vendor.avg_lead_time_days - 14)
                    factors["lead_time"] = {
                        "days": vendor.avg_lead_time_days,
                        "risk_contribution": lead_time_risk,
                    }
                    risk_score += lead_time_risk
                    recommendations.append(
                        f"Long lead time ({vendor.avg_lead_time_days} days) - consider alternatives"
                    )

            # Factor 3: Price variance
            outliers = self.variance_detector.detect_vendor_outliers(vendor_id)
            if outliers:
                outlier_risk = min(25, len(outliers) * 5)
                factors["price_variance"] = {
                    "outlier_count": len(outliers),
                    "risk_contribution": outlier_risk,
                }
                risk_score += outlier_risk
                recommendations.append(
                    f"Vendor has {len(outliers)} price outliers - review pricing strategy"
                )

            # Factor 4: Distance (if reference point provided)
            if reference_lat and reference_lon and vendor.latitude and vendor.longitude:
                distance = haversine_distance(
                    reference_lat, reference_lon,
                    vendor.latitude, vendor.longitude
                )
                if distance > 200:
                    distance_risk = min(20, (distance - 200) / 20)
                    factors["distance"] = {
                        "miles": round(distance, 1),
                        "risk_contribution": distance_risk,
                    }
                    risk_score += distance_risk
                    recommendations.append(
                        f"Vendor is {distance:.0f} miles away - consider closer alternatives"
                    )

        # Determine risk level
        risk_level = (
            RiskLevel.LOW if risk_score < 25
            else RiskLevel.MODERATE if risk_score < 50
            else RiskLevel.HIGH if risk_score < 75
            else RiskLevel.CRITICAL
        )

        return RiskAssessment(
            entity_id=vendor_id,
            entity_type="vendor",
            risk_level=risk_level,
            risk_score=min(100, risk_score),
            factors=factors,
            recommendations=recommendations,
        )

    def assess_region_risk(
        self,
        region: str,
    ) -> RiskAssessment:
        """Assess risk factors for a geographic region.

        Args:
            region: Region to assess

        Returns:
            RiskAssessment for the region
        """
        factors = {}
        recommendations = []
        risk_score = 0.0

        # Get regional benchmark
        benchmark = self.benchmarker.calculate_benchmark(region=region)

        if benchmark.sample_size == 0:
            return RiskAssessment(
                entity_id=region,
                entity_type="region",
                risk_level=RiskLevel.HIGH,
                risk_score=75.0,
                factors={"error": "No pricing data for region"},
                recommendations=["Add vendor coverage for this region"],
            )

        # Factor 1: Vendor concentration
        if benchmark.vendor_count < 3:
            concentration_risk = (3 - benchmark.vendor_count) * 15
            factors["vendor_concentration"] = {
                "vendor_count": benchmark.vendor_count,
                "risk_contribution": concentration_risk,
            }
            risk_score += concentration_risk
            recommendations.append(
                f"Low vendor diversity ({benchmark.vendor_count} vendors) - increase supplier base"
            )

        # Factor 2: Price volatility (using std/mean)
        if benchmark.price_mean > 0:
            cv = (benchmark.price_std / benchmark.price_mean) * 100
            if cv > 20:
                volatility_risk = min(25, (cv - 20) * 1.25)
                factors["price_volatility"] = {
                    "coefficient_of_variation": round(cv, 1),
                    "risk_contribution": volatility_risk,
                }
                risk_score += volatility_risk
                recommendations.append(
                    f"High price volatility in region (CV: {cv:.1f}%)"
                )

        # Factor 3: Cost index deviation
        if benchmark.cost_index > 1.2:
            cost_risk = (benchmark.cost_index - 1.0) * 20
            factors["cost_index"] = {
                "index": benchmark.cost_index,
                "risk_contribution": cost_risk,
            }
            risk_score += cost_risk
            recommendations.append(
                f"High cost region (index: {benchmark.cost_index:.2f}) - budget accordingly"
            )

        # Factor 4: Sample size
        if benchmark.sample_size < 10:
            sample_risk = (10 - benchmark.sample_size) * 3
            factors["data_quality"] = {
                "sample_size": benchmark.sample_size,
                "risk_contribution": sample_risk,
            }
            risk_score += sample_risk
            recommendations.append("Limited pricing data - increase data collection")

        risk_level = (
            RiskLevel.LOW if risk_score < 25
            else RiskLevel.MODERATE if risk_score < 50
            else RiskLevel.HIGH if risk_score < 75
            else RiskLevel.CRITICAL
        )

        return RiskAssessment(
            entity_id=region,
            entity_type="region",
            risk_level=risk_level,
            risk_score=min(100, risk_score),
            factors=factors,
            recommendations=recommendations,
        )

    def find_optimal_vendors(
        self,
        latitude: float,
        longitude: float,
        sku_ids: Optional[list[str]] = None,
        max_distance: float = 200.0,
        limit: int = 10,
    ) -> list[dict]:
        """Find optimal vendors based on proximity, reliability, and pricing.

        Args:
            latitude: Target latitude
            longitude: Target longitude
            sku_ids: Optional list of required SKUs
            max_distance: Maximum acceptable distance in miles
            limit: Maximum vendors to return

        Returns:
            List of vendor recommendations with scoring
        """
        # Get proximity scores
        proximity_results = self.proximity_scorer.score_vendors_from_point(
            latitude, longitude, limit=limit * 2
        )

        # Filter by distance
        proximity_results = [
            r for r in proximity_results if r.distance_miles <= max_distance
        ]

        recommendations = []
        for result in proximity_results[:limit]:
            # Get risk assessment
            risk = self.assess_vendor_risk(
                result.vendor_id,
                reference_lat=latitude,
                reference_lon=longitude,
            )

            # Calculate overall score
            # Higher is better: proximity * reliability * (1 - risk/100)
            overall_score = (
                result.proximity_score
                * (result.reliability_score or 0.5)
                * (1 - risk.risk_score / 100)
            )

            recommendations.append({
                "vendor_id": result.vendor_id,
                "vendor_name": result.vendor_name,
                "distance_miles": round(result.distance_miles, 1),
                "proximity_score": round(result.proximity_score, 3),
                "reliability_score": result.reliability_score,
                "risk_level": risk.risk_level.value,
                "risk_score": risk.risk_score,
                "overall_score": round(overall_score, 3),
                "recommendations": risk.recommendations[:3],
            })

        # Sort by overall score
        recommendations.sort(key=lambda x: x["overall_score"], reverse=True)
        return recommendations
