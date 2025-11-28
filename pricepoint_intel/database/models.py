"""SQLAlchemy database models for PricePoint Intel data ingestion pipeline.

Supports both SQLite (MVP) and PostgreSQL (production) via configuration flags.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import json

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Numeric,
    Index,
    UniqueConstraint,
    CheckConstraint,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# ============================================
# Enums for Type Safety
# ============================================


class MarketSizeTier(str, enum.Enum):
    """Market size classification tiers."""

    TIER_1 = "tier_1"  # Major metropolitan (>1M population)
    TIER_2 = "tier_2"  # Mid-size metro (250K-1M)
    TIER_3 = "tier_3"  # Small metro/suburban (50K-250K)
    TIER_4 = "tier_4"  # Rural (<50K)


class Currency(str, enum.Enum):
    """Supported currency codes (ISO 4217)."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    MXN = "MXN"


class ProductCategory(str, enum.Enum):
    """Product category classifications."""

    FLOORING = "flooring"
    BUILDING_MATERIALS = "building_materials"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    HVAC = "hvac"
    HARDWARE = "hardware"
    LUMBER = "lumber"
    PAINT = "paint"
    TOOLS = "tools"
    OTHER = "other"


# ============================================
# Core SKU Model
# ============================================


class SKU(Base):
    """SKU-level product data model.

    Represents individual stock keeping units with full product details.
    Designed for both SQLite (MVP) and PostgreSQL (production).
    """

    __tablename__ = "skus"

    # Primary identifier
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Product information
    product_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, default=ProductCategory.OTHER.value
    )
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Physical dimensions (for shipping/logistics)
    weight_lbs: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    length_inches: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width_inches: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_inches: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Unit of measure
    unit_of_measure: Mapped[str] = mapped_column(
        String(20), nullable=False, default="each"
    )
    units_per_case: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Supplier information (primary)
    primary_supplier_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    manufacturer_part_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    upc_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Extended attributes (JSON for flexibility)
    # PostgreSQL: Use JSONB for better performance
    # SQLite: Stored as TEXT with JSON serialization
    attributes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    vendor_prices = relationship(
        "VendorPricing", back_populates="sku", cascade="all, delete-orphan"
    )
    price_history = relationship(
        "PriceHistory", back_populates="sku", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_sku_category_name", "category", "product_name"),
        Index("idx_sku_supplier", "primary_supplier_id"),
        CheckConstraint("weight_lbs >= 0", name="ck_positive_weight"),
    )

    def __repr__(self) -> str:
        return f"<SKU(sku_id='{self.sku_id}', name='{self.product_name}')>"

    def to_dict(self) -> dict:
        """Convert SKU to dictionary representation."""
        return {
            "sku_id": self.sku_id,
            "product_name": self.product_name,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "dimensions": {
                "weight_lbs": self.weight_lbs,
                "length_inches": self.length_inches,
                "width_inches": self.width_inches,
                "height_inches": self.height_inches,
            },
            "unit_of_measure": self.unit_of_measure,
            "units_per_case": self.units_per_case,
            "supplier_info": {
                "primary_supplier_id": self.primary_supplier_id,
                "manufacturer": self.manufacturer,
                "manufacturer_part_number": self.manufacturer_part_number,
                "upc_code": self.upc_code,
            },
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "attributes": self.attributes,
        }


# ============================================
# Vendor Model
# ============================================


class Vendor(Base):
    """Vendor/Supplier master data.

    Stores information about vendors who provide pricing for SKUs.
    """

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Vendor details
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    vendor_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # distributor, manufacturer, retailer
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Location (headquarters)
    headquarters_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    headquarters_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    headquarters_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    headquarters_country: Mapped[str] = mapped_column(
        String(3), nullable=False, default="USA"
    )
    headquarters_zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Business metrics
    reliability_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0-1 scale
    avg_lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_order_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # API integration
    api_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_key_reference: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Reference to secrets manager

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    prices = relationship(
        "VendorPricing", back_populates="vendor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_vendor_location", "headquarters_state", "headquarters_city"),
        CheckConstraint(
            "reliability_score IS NULL OR (reliability_score >= 0 AND reliability_score <= 1)",
            name="ck_reliability_score_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<Vendor(vendor_id='{self.vendor_id}', name='{self.vendor_name}')>"

    def to_dict(self) -> dict:
        """Convert Vendor to dictionary representation."""
        return {
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "vendor_type": self.vendor_type,
            "contact": {
                "email": self.contact_email,
                "phone": self.contact_phone,
                "website": self.website,
            },
            "headquarters": {
                "address": self.headquarters_address,
                "city": self.headquarters_city,
                "state": self.headquarters_state,
                "country": self.headquarters_country,
                "zip": self.headquarters_zip,
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "metrics": {
                "reliability_score": self.reliability_score,
                "avg_lead_time_days": self.avg_lead_time_days,
                "min_order_value": self.min_order_value,
            },
            "api_enabled": self.api_enabled,
            "is_active": self.is_active,
        }


# ============================================
# Vendor Pricing Model
# ============================================


class VendorPricing(Base):
    """Vendor-specific pricing for SKUs.

    Tracks pricing by vendor, region, and currency with full audit trail.
    """

    __tablename__ = "vendor_pricing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    sku_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("skus.sku_id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("vendors.vendor_id", ondelete="CASCADE"), nullable=False
    )
    market_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("geographic_markets.market_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Pricing data
    price: Mapped[float] = mapped_column(
        Numeric(12, 4), nullable=False
    )  # High precision for pricing
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default=Currency.USD.value
    )
    price_per_unit: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 4), nullable=True
    )  # Normalized price
    unit_of_measure: Mapped[str] = mapped_column(
        String(20), nullable=False, default="each"
    )

    # Volume pricing tiers (stored as JSON)
    volume_pricing: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # {min_qty: price, ...}

    # Geographic scope
    geographic_region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # Validity period
    effective_date: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    expiration_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Data quality
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0-1 scale
    data_source: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # api, csv_import, manual, web_scrape
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Audit
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    sku = relationship("SKU", back_populates="vendor_prices")
    vendor = relationship("Vendor", back_populates="prices")
    market = relationship("GeographicMarket", back_populates="vendor_prices")

    __table_args__ = (
        UniqueConstraint(
            "sku_id",
            "vendor_id",
            "geographic_region",
            "effective_date",
            name="uq_vendor_sku_region_date",
        ),
        Index("idx_pricing_sku_vendor", "sku_id", "vendor_id"),
        Index("idx_pricing_region", "geographic_region"),
        Index("idx_pricing_last_updated", "last_updated"),
        CheckConstraint("price >= 0", name="ck_positive_price"),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_confidence_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<VendorPricing(sku='{self.sku_id}', vendor='{self.vendor_id}', price={self.price})>"

    def to_dict(self) -> dict:
        """Convert VendorPricing to dictionary representation."""
        return {
            "sku_id": self.sku_id,
            "vendor_id": self.vendor_id,
            "market_id": self.market_id,
            "price": float(self.price),
            "currency": self.currency,
            "price_per_unit": float(self.price_per_unit) if self.price_per_unit else None,
            "unit_of_measure": self.unit_of_measure,
            "volume_pricing": self.volume_pricing,
            "geographic_region": self.geographic_region,
            "effective_date": self.effective_date.isoformat()
            if self.effective_date
            else None,
            "expiration_date": self.expiration_date.isoformat()
            if self.expiration_date
            else None,
            "confidence_score": self.confidence_score,
            "data_source": self.data_source,
            "is_verified": self.is_verified,
            "last_updated": self.last_updated.isoformat()
            if self.last_updated
            else None,
        }


# ============================================
# Geographic Market Model
# ============================================


class GeographicMarket(Base):
    """Geographic market definitions for regional analysis.

    Stores market regions with coordinates for geospatial analysis.
    """

    __tablename__ = "geographic_markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Geographic details
    region_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    region_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # State/province code
    country_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USA")

    # Coordinates (centroid of region)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Bounding box for regional queries
    bbox_north: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_south: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_east: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_west: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Market classification
    market_size_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MarketSizeTier.TIER_3.value
    )
    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gdp_per_capita: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Cost indices for normalization
    cost_of_living_index: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )  # 1.0 = national average
    regional_price_multiplier: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    vendor_prices = relationship("VendorPricing", back_populates="market")
    distribution_centers = relationship(
        "DistributionCenter", back_populates="market", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_market_coordinates", "latitude", "longitude"),
        Index("idx_market_tier", "market_size_tier"),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_valid_latitude"
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="ck_valid_longitude"
        ),
    )

    def __repr__(self) -> str:
        return f"<GeographicMarket(market_id='{self.market_id}', region='{self.region_name}')>"

    def to_dict(self) -> dict:
        """Convert GeographicMarket to dictionary representation."""
        return {
            "market_id": self.market_id,
            "region_name": self.region_name,
            "region_code": self.region_code,
            "country_code": self.country_code,
            "coordinates": {"latitude": self.latitude, "longitude": self.longitude},
            "bounding_box": {
                "north": self.bbox_north,
                "south": self.bbox_south,
                "east": self.bbox_east,
                "west": self.bbox_west,
            },
            "market_size_tier": self.market_size_tier,
            "population": self.population,
            "gdp_per_capita": self.gdp_per_capita,
            "cost_indices": {
                "cost_of_living_index": self.cost_of_living_index,
                "regional_price_multiplier": self.regional_price_multiplier,
            },
            "is_active": self.is_active,
        }


# ============================================
# Distribution Center Model
# ============================================


class DistributionCenter(Base):
    """Distribution centers for geospatial risk analysis.

    Used for proximity scoring and logistics calculations.
    """

    __tablename__ = "distribution_centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    center_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Foreign key
    market_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("geographic_markets.market_id", ondelete="SET NULL"),
        nullable=True,
    )
    vendor_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("vendors.vendor_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Center details
    center_name: Mapped[str] = mapped_column(String(255), nullable=False)
    center_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="warehouse"
    )  # warehouse, fulfillment, crossdock

    # Location
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(3), nullable=False, default="USA")
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Operational details
    square_footage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_daily_shipments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    service_radius_miles: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    market = relationship("GeographicMarket", back_populates="distribution_centers")

    __table_args__ = (
        Index("idx_dc_coordinates", "latitude", "longitude"),
        Index("idx_dc_market", "market_id"),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_dc_valid_latitude"
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="ck_dc_valid_longitude"
        ),
    )

    def __repr__(self) -> str:
        return f"<DistributionCenter(center_id='{self.center_id}', city='{self.city}')>"

    def to_dict(self) -> dict:
        """Convert DistributionCenter to dictionary representation."""
        return {
            "center_id": self.center_id,
            "market_id": self.market_id,
            "vendor_id": self.vendor_id,
            "center_name": self.center_name,
            "center_type": self.center_type,
            "location": {
                "address": self.address,
                "city": self.city,
                "state": self.state,
                "country": self.country,
                "zip_code": self.zip_code,
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "operations": {
                "square_footage": self.square_footage,
                "max_daily_shipments": self.max_daily_shipments,
                "service_radius_miles": self.service_radius_miles,
            },
            "is_active": self.is_active,
        }


# ============================================
# Price History Model
# ============================================


class PriceHistory(Base):
    """Historical price tracking for trend analysis.

    Stores price snapshots over time for forecasting and anomaly detection.
    """

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    sku_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("skus.sku_id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("vendors.vendor_id", ondelete="CASCADE"), nullable=False
    )

    # Price snapshot
    price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default=Currency.USD.value
    )
    geographic_region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # Timestamp
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    # Change tracking
    price_change_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # % change from previous
    is_anomaly: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Flagged as unusual

    # Data source
    data_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    sku = relationship("SKU", back_populates="price_history")

    __table_args__ = (
        Index("idx_history_sku_date", "sku_id", "recorded_at"),
        Index("idx_history_vendor_date", "vendor_id", "recorded_at"),
        Index("idx_history_anomaly", "is_anomaly"),
        CheckConstraint("price >= 0", name="ck_history_positive_price"),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory(sku='{self.sku_id}', price={self.price}, date='{self.recorded_at}')>"

    def to_dict(self) -> dict:
        """Convert PriceHistory to dictionary representation."""
        return {
            "sku_id": self.sku_id,
            "vendor_id": self.vendor_id,
            "price": float(self.price),
            "currency": self.currency,
            "geographic_region": self.geographic_region,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "price_change_pct": self.price_change_pct,
            "is_anomaly": self.is_anomaly,
            "data_source": self.data_source,
        }
