"""FastAPI routes for data ingestion endpoints.

Provides REST API for bulk data import, validation, and geospatial analysis.
"""

import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from pricepoint_intel.database.connection import (
    DatabaseConfig,
    init_database,
    check_connection,
    get_database_info,
    session_scope,
)
from pricepoint_intel.database.models import SKU, Vendor, VendorPricing, GeographicMarket
from pricepoint_intel.ingestion.csv_importer import CSVImporter, ImportConfig, ImportStats
from pricepoint_intel.ingestion.validators import (
    SKUValidator,
    PricingValidator,
    MarketValidator,
    VendorValidator,
    ValidationResult,
)
from pricepoint_intel.geospatial.risk_framework import (
    GeospatialRiskAnalyzer,
    ProximityScorer,
    VarianceDetector,
    RegionalBenchmarker,
)

# Create router
router = APIRouter(prefix="/v1/ingestion", tags=["Data Ingestion"])


# ============================================
# Request/Response Models
# ============================================


class DatabaseStatusResponse(BaseModel):
    """Database status response."""

    connected: bool
    database_type: str
    database_name: str
    pool_size: int


class ImportResponse(BaseModel):
    """Response for import operations."""

    success: bool
    total_rows: int
    successful: int
    failed: int
    skipped: int
    warnings: int
    duration_seconds: Optional[float] = None
    errors: list = Field(default_factory=list)


class ValidationRequest(BaseModel):
    """Request for single record validation."""

    data_type: str = Field(..., description="Type: sku, pricing, vendor, or market")
    data: dict = Field(..., description="Record data to validate")


class ValidationResponse(BaseModel):
    """Response for validation operations."""

    is_valid: bool
    error_count: int
    warning_count: int
    errors: list = Field(default_factory=list)
    warnings: list = Field(default_factory=list)
    cleaned_data: Optional[dict] = None


class SKUSearchRequest(BaseModel):
    """Request for SKU search."""

    query: Optional[str] = None
    category: Optional[str] = None
    supplier_id: Optional[str] = None
    region: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class SKUResponse(BaseModel):
    """SKU with pricing summary."""

    sku_id: str
    product_name: str
    category: str
    manufacturer: Optional[str] = None
    avg_price: Optional[float] = None
    price_range: Optional[tuple[float, float]] = None
    vendor_count: int = 0


class SKUSearchResponse(BaseModel):
    """Response for SKU search."""

    items: list[SKUResponse]
    total: int
    page: int
    page_size: int


class ProximityRequest(BaseModel):
    """Request for vendor proximity analysis."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    max_distance_miles: float = Field(200, ge=1, le=1000)
    min_reliability: Optional[float] = Field(None, ge=0, le=1)
    limit: int = Field(20, ge=1, le=100)


class ProximityResult(BaseModel):
    """Result of proximity analysis."""

    vendor_id: str
    vendor_name: str
    distance_miles: float
    proximity_score: float
    reliability_score: Optional[float] = None
    composite_score: float


class ProximityResponse(BaseModel):
    """Response for proximity analysis."""

    reference_point: dict
    vendors: list[ProximityResult]
    total_found: int


class VarianceResult(BaseModel):
    """Pricing variance result."""

    sku_id: str
    product_name: str
    region: str
    price: float
    regional_mean: float
    z_score: float
    variance_pct: float
    is_anomaly: bool
    anomaly_type: Optional[str] = None


class VarianceResponse(BaseModel):
    """Response for variance detection."""

    anomalies: list[VarianceResult]
    total_analyzed: int
    anomaly_count: int


class BenchmarkResult(BaseModel):
    """Regional benchmark result."""

    region: str
    sku_count: int
    vendor_count: int
    price_mean: float
    price_median: float
    price_min: float
    price_max: float
    percentile_25: float
    percentile_75: float
    cost_index: float


class BenchmarkResponse(BaseModel):
    """Response for regional benchmarking."""

    benchmarks: list[BenchmarkResult]


class RiskAssessmentRequest(BaseModel):
    """Request for risk assessment."""

    entity_type: str = Field(..., description="vendor or region")
    entity_id: str
    reference_latitude: Optional[float] = None
    reference_longitude: Optional[float] = None


class RiskAssessmentResponse(BaseModel):
    """Response for risk assessment."""

    entity_id: str
    entity_type: str
    risk_level: str
    risk_score: float
    factors: dict
    recommendations: list[str]


# ============================================
# Database Endpoints
# ============================================


@router.get("/database/status", response_model=DatabaseStatusResponse)
async def get_database_status():
    """Get current database connection status.

    Returns information about the database connection and configuration.

    **PostgreSQL Flag**: Set `DATABASE_URL` environment variable to switch
    from SQLite (default) to PostgreSQL for production.
    """
    config = DatabaseConfig.from_env()
    info = get_database_info(config)
    connected = check_connection(config)

    return DatabaseStatusResponse(
        connected=connected,
        database_type=info["type"],
        database_name=info["database"],
        pool_size=info["pool_size"],
    )


@router.post("/database/initialize")
async def initialize_database(drop_existing: bool = False):
    """Initialize database schema.

    Creates all required tables for the data ingestion pipeline.
    Use `drop_existing=true` to reset the database (WARNING: destroys data).

    **Tables Created**:
    - `skus`: SKU-level product data
    - `vendors`: Vendor master data
    - `vendor_pricing`: Vendor-specific pricing
    - `geographic_markets`: Market region definitions
    - `distribution_centers`: Distribution center locations
    - `price_history`: Historical price tracking
    """
    try:
        config = DatabaseConfig.from_env()
        init_database(config, drop_existing=drop_existing)
        return {
            "success": True,
            "message": "Database initialized successfully",
            "tables_created": [
                "skus",
                "vendors",
                "vendor_pricing",
                "geographic_markets",
                "distribution_centers",
                "price_history",
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")


# ============================================
# Validation Endpoints
# ============================================


@router.post("/validate", response_model=ValidationResponse)
async def validate_record(body: ValidationRequest):
    """Validate a single data record.

    Validates a record against the schema for the specified data type.
    Returns validation errors, warnings, and cleaned data.

    **Data Types**:
    - `sku`: SKU product data
    - `pricing`: Vendor pricing data
    - `vendor`: Vendor master data
    - `market`: Geographic market data
    """
    validators = {
        "sku": SKUValidator(),
        "pricing": PricingValidator(),
        "vendor": VendorValidator(),
        "market": MarketValidator(),
    }

    validator = validators.get(body.data_type.lower())
    if not validator:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data_type. Must be one of: {list(validators.keys())}",
        )

    result = validator.validate(body.data)

    return ValidationResponse(
        is_valid=result.is_valid,
        error_count=result.error_count,
        warning_count=result.warning_count,
        errors=[e.to_dict() for e in result.errors],
        warnings=[w.to_dict() for w in result.warnings],
        cleaned_data=result.cleaned_data if result.is_valid else None,
    )


@router.post("/validate/batch")
async def validate_batch(
    data_type: str = Query(..., description="Data type: sku, pricing, vendor, market"),
    file: UploadFile = File(..., description="CSV file to validate"),
):
    """Validate a batch of records from CSV file.

    Performs dry-run validation without writing to database.
    Returns summary of validation results.
    """
    config = DatabaseConfig.from_env()
    import_config = ImportConfig(dry_run=True)
    importer = CSVImporter(config, import_config)

    # Read file content
    content = await file.read()
    file_obj = io.StringIO(content.decode("utf-8"))

    # Run validation based on type
    if data_type == "sku":
        stats = importer.import_skus(file_obj)
    elif data_type == "pricing":
        stats = importer.import_pricing(file_obj)
    elif data_type == "vendor":
        stats = importer.import_vendors(file_obj)
    elif data_type == "market":
        stats = importer.import_markets(file_obj)
    else:
        raise HTTPException(status_code=400, detail="Invalid data_type")

    return ImportResponse(
        success=stats.failed == 0,
        total_rows=stats.total_rows,
        successful=stats.successful,
        failed=stats.failed,
        skipped=stats.skipped,
        warnings=stats.warnings,
        duration_seconds=stats.duration_seconds,
        errors=stats.errors[:50],
    )


# ============================================
# Import Endpoints
# ============================================


@router.post("/import/skus", response_model=ImportResponse)
async def import_skus(
    file: UploadFile = File(..., description="CSV file with SKU data"),
    update_existing: bool = Query(True, description="Update existing records"),
):
    """Import SKU data from CSV file.

    **Required Columns**:
    - `sku_id`: Unique SKU identifier
    - `product_name`: Product name
    - `category`: Product category

    **Optional Columns**:
    - `description`, `subcategory`, `weight_lbs`, `length_inches`,
    - `width_inches`, `height_inches`, `unit_of_measure`, `units_per_case`,
    - `primary_supplier_id`, `manufacturer`, `manufacturer_part_number`, `upc_code`
    """
    config = DatabaseConfig.from_env()
    import_config = ImportConfig(update_existing=update_existing)
    importer = CSVImporter(config, import_config)

    content = await file.read()
    file_obj = io.StringIO(content.decode("utf-8"))

    stats = importer.import_skus(file_obj)

    return ImportResponse(
        success=stats.failed == 0,
        total_rows=stats.total_rows,
        successful=stats.successful,
        failed=stats.failed,
        skipped=stats.skipped,
        warnings=stats.warnings,
        duration_seconds=stats.duration_seconds,
        errors=stats.errors[:50],
    )


@router.post("/import/vendors", response_model=ImportResponse)
async def import_vendors(
    file: UploadFile = File(..., description="CSV file with vendor data"),
    update_existing: bool = Query(True, description="Update existing records"),
):
    """Import vendor data from CSV file.

    **Required Columns**:
    - `vendor_id`: Unique vendor identifier
    - `vendor_name`: Vendor name

    **Optional Columns**:
    - `vendor_type`, `contact_email`, `contact_phone`, `website`,
    - `headquarters_city`, `headquarters_state`, `headquarters_country`,
    - `latitude`, `longitude`, `reliability_score`, `avg_lead_time_days`
    """
    config = DatabaseConfig.from_env()
    import_config = ImportConfig(update_existing=update_existing)
    importer = CSVImporter(config, import_config)

    content = await file.read()
    file_obj = io.StringIO(content.decode("utf-8"))

    stats = importer.import_vendors(file_obj)

    return ImportResponse(
        success=stats.failed == 0,
        total_rows=stats.total_rows,
        successful=stats.successful,
        failed=stats.failed,
        skipped=stats.skipped,
        warnings=stats.warnings,
        duration_seconds=stats.duration_seconds,
        errors=stats.errors[:50],
    )


@router.post("/import/pricing", response_model=ImportResponse)
async def import_pricing(
    file: UploadFile = File(..., description="CSV file with pricing data"),
    update_existing: bool = Query(True, description="Update existing records"),
):
    """Import vendor pricing data from CSV file.

    **Required Columns**:
    - `sku_id`: SKU identifier (must exist in database)
    - `vendor_id`: Vendor identifier (must exist in database)
    - `price`: Unit price

    **Optional Columns**:
    - `currency`, `geographic_region`, `effective_date`, `expiration_date`,
    - `confidence_score`, `data_source`, `volume_pricing`

    **Note**: SKUs and vendors must be imported first.
    """
    config = DatabaseConfig.from_env()
    import_config = ImportConfig(update_existing=update_existing)
    importer = CSVImporter(config, import_config)

    content = await file.read()
    file_obj = io.StringIO(content.decode("utf-8"))

    stats = importer.import_pricing(file_obj)

    return ImportResponse(
        success=stats.failed == 0,
        total_rows=stats.total_rows,
        successful=stats.successful,
        failed=stats.failed,
        skipped=stats.skipped,
        warnings=stats.warnings,
        duration_seconds=stats.duration_seconds,
        errors=stats.errors[:50],
    )


@router.post("/import/markets", response_model=ImportResponse)
async def import_markets(
    file: UploadFile = File(..., description="CSV file with market data"),
    update_existing: bool = Query(True, description="Update existing records"),
):
    """Import geographic market data from CSV file.

    **Required Columns**:
    - `market_id`: Unique market identifier
    - `region_name`: Region name
    - `latitude`: Center latitude
    - `longitude`: Center longitude

    **Optional Columns**:
    - `region_code`, `country_code`, `market_size_tier`, `population`,
    - `gdp_per_capita`, `cost_of_living_index`, `regional_price_multiplier`
    """
    config = DatabaseConfig.from_env()
    import_config = ImportConfig(update_existing=update_existing)
    importer = CSVImporter(config, import_config)

    content = await file.read()
    file_obj = io.StringIO(content.decode("utf-8"))

    stats = importer.import_markets(file_obj)

    return ImportResponse(
        success=stats.failed == 0,
        total_rows=stats.total_rows,
        successful=stats.successful,
        failed=stats.failed,
        skipped=stats.skipped,
        warnings=stats.warnings,
        duration_seconds=stats.duration_seconds,
        errors=stats.errors[:50],
    )


# ============================================
# Search Endpoints
# ============================================


@router.post("/search/skus", response_model=SKUSearchResponse)
async def search_skus(body: SKUSearchRequest):
    """Search SKUs with filters.

    Search and filter SKUs by name, category, supplier, or region.
    Returns SKUs with pricing summary.
    """
    config = DatabaseConfig.from_env()

    with session_scope(config) as session:
        query = session.query(SKU).filter(SKU.is_active == True)

        # Apply filters
        if body.query:
            search_term = f"%{body.query}%"
            query = query.filter(
                (SKU.sku_id.ilike(search_term))
                | (SKU.product_name.ilike(search_term))
                | (SKU.description.ilike(search_term))
            )

        if body.category:
            query = query.filter(SKU.category == body.category)

        if body.supplier_id:
            query = query.filter(SKU.primary_supplier_id == body.supplier_id)

        # Get total count
        total = query.count()

        # Paginate
        offset = (body.page - 1) * body.page_size
        skus = query.offset(offset).limit(body.page_size).all()

        # Build response with pricing summary
        items = []
        for sku in skus:
            # Get pricing data
            prices = (
                session.query(VendorPricing.price)
                .filter(VendorPricing.sku_id == sku.sku_id)
                .all()
            )

            price_values = [float(p[0]) for p in prices]

            items.append(
                SKUResponse(
                    sku_id=sku.sku_id,
                    product_name=sku.product_name,
                    category=sku.category,
                    manufacturer=sku.manufacturer,
                    avg_price=sum(price_values) / len(price_values) if price_values else None,
                    price_range=(min(price_values), max(price_values)) if price_values else None,
                    vendor_count=len(price_values),
                )
            )

        return SKUSearchResponse(
            items=items,
            total=total,
            page=body.page,
            page_size=body.page_size,
        )


# ============================================
# Geospatial Analysis Endpoints
# ============================================


@router.post("/analysis/proximity", response_model=ProximityResponse)
async def analyze_vendor_proximity(body: ProximityRequest):
    """Analyze vendor proximity to a geographic point.

    Calculates distance and proximity scores for vendors relative to
    a reference point (e.g., distribution center, project site).

    **Scoring**:
    - Proximity score: Exponential decay based on distance (0-1)
    - Composite score: Weighted combination of proximity + reliability
    """
    config = DatabaseConfig.from_env()
    scorer = ProximityScorer(config, max_distance_miles=body.max_distance_miles)

    results = scorer.score_vendors_from_point(
        latitude=body.latitude,
        longitude=body.longitude,
        limit=body.limit,
        min_reliability=body.min_reliability,
    )

    return ProximityResponse(
        reference_point={"latitude": body.latitude, "longitude": body.longitude},
        vendors=[
            ProximityResult(
                vendor_id=r.vendor_id,
                vendor_name=r.vendor_name,
                distance_miles=round(r.distance_miles, 2),
                proximity_score=round(r.proximity_score, 3),
                reliability_score=r.reliability_score,
                composite_score=round(r.composite_score, 3),
            )
            for r in results
        ],
        total_found=len(results),
    )


@router.get("/analysis/variance", response_model=VarianceResponse)
async def detect_pricing_variance(
    sku_id: Optional[str] = Query(None, description="Filter by SKU ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    z_threshold: float = Query(2.0, ge=1.0, le=5.0, description="Z-score threshold"),
):
    """Detect pricing variance and anomalies.

    Identifies pricing outliers by comparing against regional averages.
    Uses z-score analysis to flag anomalies.

    **Anomaly Types**:
    - `price_spike`: Significantly above regional average
    - `price_drop`: Significantly below regional average
    - `vendor_outlier`: Vendor's price differs from market
    """
    config = DatabaseConfig.from_env()
    detector = VarianceDetector(config, z_score_threshold=z_threshold)

    anomalies = detector.detect_regional_anomalies(sku_id=sku_id, category=category)

    return VarianceResponse(
        anomalies=[
            VarianceResult(
                sku_id=a.sku_id,
                product_name=a.product_name,
                region=a.region,
                price=round(a.price, 2),
                regional_mean=round(a.regional_mean, 2),
                z_score=round(a.z_score, 2),
                variance_pct=round(a.variance_pct, 2),
                is_anomaly=a.is_anomaly,
                anomaly_type=a.anomaly_type.value if a.anomaly_type else None,
            )
            for a in anomalies
        ],
        total_analyzed=len(anomalies),
        anomaly_count=sum(1 for a in anomalies if a.is_anomaly),
    )


@router.get("/analysis/benchmarks", response_model=BenchmarkResponse)
async def get_regional_benchmarks(
    regions: Optional[str] = Query(None, description="Comma-separated region names"),
    category: Optional[str] = Query(None, description="Product category filter"),
):
    """Get pricing benchmarks by region.

    Aggregates pricing statistics for specified regions including:
    - Mean, median, min/max prices
    - Percentile distribution (25th, 75th)
    - Regional cost index
    """
    config = DatabaseConfig.from_env()
    benchmarker = RegionalBenchmarker(config)

    if regions:
        region_list = [r.strip() for r in regions.split(",")]
        results = benchmarker.compare_regions(region_list, category=category)
    else:
        # Get all regions from database
        with session_scope(config) as session:
            market_regions = (
                session.query(GeographicMarket.region_name)
                .filter(GeographicMarket.is_active == True)
                .all()
            )
            region_list = [r[0] for r in market_regions]

        if not region_list:
            # Return overall benchmark
            overall = benchmarker.calculate_benchmark(category=category)
            results = [overall]
        else:
            results = benchmarker.compare_regions(region_list, category=category)

    return BenchmarkResponse(
        benchmarks=[
            BenchmarkResult(
                region=b.region,
                sku_count=b.sku_count,
                vendor_count=b.vendor_count,
                price_mean=round(b.price_mean, 2),
                price_median=round(b.price_median, 2),
                price_min=round(b.price_min, 2),
                price_max=round(b.price_max, 2),
                percentile_25=round(b.percentile_25, 2),
                percentile_75=round(b.percentile_75, 2),
                cost_index=round(b.cost_index, 3),
            )
            for b in results
            if b.sample_size > 0
        ]
    )


@router.post("/analysis/risk", response_model=RiskAssessmentResponse)
async def assess_risk(body: RiskAssessmentRequest):
    """Assess risk for a vendor or region.

    Performs comprehensive risk analysis considering:
    - Reliability scores
    - Lead times
    - Price variance
    - Geographic distance (if reference point provided)
    - Vendor concentration

    Returns risk level (low/moderate/high/critical) with recommendations.
    """
    config = DatabaseConfig.from_env()
    analyzer = GeospatialRiskAnalyzer(config)

    if body.entity_type.lower() == "vendor":
        assessment = analyzer.assess_vendor_risk(
            body.entity_id,
            reference_lat=body.reference_latitude,
            reference_lon=body.reference_longitude,
        )
    elif body.entity_type.lower() == "region":
        assessment = analyzer.assess_region_risk(body.entity_id)
    else:
        raise HTTPException(
            status_code=400, detail="entity_type must be 'vendor' or 'region'"
        )

    return RiskAssessmentResponse(
        entity_id=assessment.entity_id,
        entity_type=assessment.entity_type,
        risk_level=assessment.risk_level.value,
        risk_score=round(assessment.risk_score, 1),
        factors=assessment.factors,
        recommendations=assessment.recommendations,
    )


# ============================================
# Statistics Endpoints
# ============================================


@router.get("/stats/summary")
async def get_data_summary():
    """Get summary statistics for all data.

    Returns counts and basic statistics for SKUs, vendors,
    pricing records, and markets.
    """
    config = DatabaseConfig.from_env()

    with session_scope(config) as session:
        sku_count = session.query(SKU).filter(SKU.is_active == True).count()
        vendor_count = session.query(Vendor).filter(Vendor.is_active == True).count()
        pricing_count = session.query(VendorPricing).count()
        market_count = session.query(GeographicMarket).filter(GeographicMarket.is_active == True).count()

        # Get category breakdown
        from sqlalchemy import func

        categories = (
            session.query(SKU.category, func.count(SKU.sku_id))
            .filter(SKU.is_active == True)
            .group_by(SKU.category)
            .all()
        )

        # Get region breakdown
        regions = (
            session.query(
                VendorPricing.geographic_region, func.count(VendorPricing.id)
            )
            .filter(VendorPricing.geographic_region.isnot(None))
            .group_by(VendorPricing.geographic_region)
            .all()
        )

        return {
            "totals": {
                "skus": sku_count,
                "vendors": vendor_count,
                "pricing_records": pricing_count,
                "markets": market_count,
            },
            "by_category": {cat: count for cat, count in categories},
            "by_region": {region: count for region, count in regions if region},
            "generated_at": datetime.utcnow().isoformat(),
        }
