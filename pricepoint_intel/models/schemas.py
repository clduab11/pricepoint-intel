"""Pydantic schemas for API requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field

# ============================================
# Promotional Inference Schemas
# ============================================


class PromoSimulationRequest(BaseModel):
    """Request schema for promotional simulation endpoint."""

    sku_id: str = Field(..., description="SKU identifier")
    current_price: float = Field(..., gt=0, description="Current price of the product")
    promo_type: Literal["volume", "percentage"] = Field(
        ..., description="Type of promotion: volume discount or percentage off"
    )
    promo_value: float = Field(
        ..., ge=0, description="User's slider position (volume count or percentage)"
    )
    location_code: str = Field(..., description="Geographic location code (zip code)")
    seasonality_factor: float | None = Field(
        None, ge=0, le=2, description="Seasonality multiplier (0-2, 1 is neutral)"
    )
    inventory_level: int | None = Field(
        None, ge=0, description="Current inventory level"
    )
    competitor_prices: list[float] | None = Field(
        None, description="List of competitor prices for the same or similar SKU"
    )


class PromoSimulationResponse(BaseModel):
    """Response schema for promotional simulation endpoint."""

    projected_lift: float = Field(
        ..., description="Projected sales lift as a percentage"
    )
    confidence_interval: tuple[float, float] = Field(
        ..., description="Confidence interval for the projected lift (lower, upper)"
    )
    ai_recommended_value: float = Field(
        ..., description="AI recommended promo value for optimal results"
    )
    calibration_score: float = Field(
        ..., ge=0, le=1, description="Calibration score indicating model confidence"
    )
    latency_ms: float = Field(..., ge=0, description="Inference latency in milliseconds")
    model_version: str = Field(..., description="Version of the ML model used")


# ============================================
# Pricing Query Schemas
# ============================================


class PricingQueryRequest(BaseModel):
    """Request schema for natural language intelligence query."""

    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query")
    location: str | None = Field(None, description="Location filter (zip code or city)")
    radius_miles: int = Field(50, ge=1, le=500, description="Search radius in miles")
    max_results: int = Field(50, ge=1, le=100, description="Maximum number of results")


class VendorInfo(BaseModel):
    """Vendor information in response."""

    vendor_id: str
    vendor_name: str
    price_per_unit: float
    unit: str
    distance_miles: float
    last_updated: str
    confidence_score: float = Field(ge=0, le=1)


class BenchmarkData(BaseModel):
    """Benchmark data in response."""

    industry_average: float
    geographic_premium: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    unit: str


class PriceHistoryEntry(BaseModel):
    """Price history entry."""

    date: str
    price: float


class PricingData(BaseModel):
    """Individual SKU pricing data."""

    sku_id: str
    product_name: str
    current_price: float
    unit: str
    vendor_id: str
    vendor_name: str
    location: str
    last_updated: str
    price_history: list[PriceHistoryEntry] | None = None


class PricingQueryResponse(BaseModel):
    """Response schema for natural language intelligence query."""

    product: str
    location: str
    radius_miles: int
    vendor_count: int
    price_range: tuple[float, float] | None
    market_average: float | None
    vendors: list[VendorInfo]
    benchmark: BenchmarkData | None = None
    query_time_ms: float


# ============================================
# Vendor Discovery Schemas
# ============================================


class VendorDiscoveryResponse(BaseModel):
    """Response schema for vendor discovery endpoint."""

    location: str
    vendors: list[VendorInfo]
    total_count: int
    page: int
    page_size: int


# ============================================
# Benchmark Schemas
# ============================================


class CategoryBenchmarkResponse(BaseModel):
    """Response schema for category benchmarking endpoint."""

    product_category: str
    benchmark: BenchmarkData
    sample_size: int
    data_freshness_days: int
    geographic_coverage: list[str]
