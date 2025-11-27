"""FastAPI application for PricePoint Intel API."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from pricepoint_intel import IntelligenceEngine
from pricepoint_intel.intelligence_engine.predictive_models import PriceForecaster
from pricepoint_intel.models.schemas import (
    BenchmarkData,
    CategoryBenchmarkResponse,
    PriceHistoryEntry,
    PricingData,
    PricingQueryRequest,
    PricingQueryResponse,
    PromoSimulationRequest,
    PromoSimulationResponse,
    VendorDiscoveryResponse,
    VendorInfo,
)

# Version info
MODEL_VERSION = "1.0.0"

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    app.state.engine = IntelligenceEngine()
    app.state.forecaster = PriceForecaster()
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="PricePoint Intel API",
    description="SKU-Level Competitive Intelligence Platform for Real-Time Cost Analysis & Vendor Discovery",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")


# ============================================
# Health Check
# ============================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": MODEL_VERSION}


# ============================================
# Promotional Inference Endpoint
# ============================================


@app.post("/v1/inference/simulate-promo", response_model=PromoSimulationResponse)
@limiter.limit("60/minute")
async def simulate_promo(request: Request, body: PromoSimulationRequest):
    """Simulate promotional campaign lift.

    This endpoint provides AI-powered promotional recommendations
    with confidence intervals.
    """
    start_time = time.time()

    forecaster: PriceForecaster = request.app.state.forecaster

    # Run simulation
    result = forecaster.simulate_promo_lift(
        current_price=body.current_price,
        promo_type=body.promo_type,
        promo_value=body.promo_value,
        seasonality_factor=body.seasonality_factor or 1.0,
        inventory_level=body.inventory_level,
        competitor_prices=body.competitor_prices,
    )

    latency_ms = (time.time() - start_time) * 1000

    return PromoSimulationResponse(
        projected_lift=result["projected_lift"],
        confidence_interval=result["confidence_interval"],
        ai_recommended_value=result["ai_recommended_value"],
        calibration_score=result["calibration_score"],
        latency_ms=latency_ms,
        model_version=MODEL_VERSION,
    )


# ============================================
# Pricing Endpoint
# ============================================


@app.get("/v1/pricing/{sku_id}", response_model=PricingData)
@limiter.limit("60/minute")
async def get_pricing(request: Request, sku_id: str):
    """Get current pricing data for a specific SKU."""
    # In production, this would query the database
    return PricingData(
        sku_id=sku_id,
        product_name=f"Product {sku_id}",
        current_price=2.99,
        unit="sqft",
        vendor_id="V001",
        vendor_name="Sample Vendor",
        location="35242",
        last_updated="2024-01-15",
        price_history=[
            PriceHistoryEntry(date="2024-01-01", price=2.89),
            PriceHistoryEntry(date="2024-01-08", price=2.95),
            PriceHistoryEntry(date="2024-01-15", price=2.99),
        ],
    )


# ============================================
# Natural Language Query Endpoint
# ============================================


@app.post("/v1/query", response_model=PricingQueryResponse)
@limiter.limit("60/minute")
async def query_intelligence(request: Request, body: PricingQueryRequest):
    """Execute a natural language intelligence query."""
    start_time = time.time()

    engine: IntelligenceEngine = request.app.state.engine

    # Parse and execute query
    results = engine.query(
        product=body.query,
        location=body.location or "35242",
        radius_miles=body.radius_miles,
        max_vendors=body.max_results,
    )

    query_time_ms = (time.time() - start_time) * 1000

    # Convert to response format
    vendors = [
        VendorInfo(
            vendor_id=v.vendor_id,
            vendor_name=v.vendor_name,
            price_per_unit=v.price_per_unit,
            unit=v.unit,
            distance_miles=v.distance_miles,
            last_updated=v.last_updated,
            confidence_score=v.confidence_score,
        )
        for v in results.vendors
    ]

    benchmark = None
    if results.benchmark:
        benchmark = BenchmarkData(
            industry_average=results.benchmark.industry_average,
            geographic_premium=results.benchmark.geographic_premium,
            percentile_25=results.benchmark.percentile_25,
            percentile_50=results.benchmark.percentile_50,
            percentile_75=results.benchmark.percentile_75,
            unit=results.benchmark.unit,
        )

    return PricingQueryResponse(
        product=results.product,
        location=results.location,
        radius_miles=results.radius_miles,
        vendor_count=results.vendor_count,
        price_range=results.price_range,
        market_average=results.market_average,
        vendors=vendors,
        benchmark=benchmark,
        query_time_ms=query_time_ms,
    )


# ============================================
# Vendor Discovery Endpoint
# ============================================


@app.get("/v1/vendors/{location}", response_model=VendorDiscoveryResponse)
@limiter.limit("60/minute")
async def discover_vendors(
    request: Request,
    location: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Discover vendors by location."""
    engine: IntelligenceEngine = request.app.state.engine

    # Get all vendors for location
    results = engine.query(
        product="flooring",  # Default product
        location=location,
        radius_miles=50,
        max_vendors=page_size * page,
    )

    # Paginate
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_vendors = results.vendors[start_idx:end_idx]

    vendors = [
        VendorInfo(
            vendor_id=v.vendor_id,
            vendor_name=v.vendor_name,
            price_per_unit=v.price_per_unit,
            unit=v.unit,
            distance_miles=v.distance_miles,
            last_updated=v.last_updated,
            confidence_score=v.confidence_score,
        )
        for v in paginated_vendors
    ]

    return VendorDiscoveryResponse(
        location=location,
        vendors=vendors,
        total_count=len(results.vendors),
        page=page,
        page_size=page_size,
    )


# ============================================
# Benchmarks Endpoint
# ============================================


@app.get("/v1/benchmarks/{product_category}", response_model=CategoryBenchmarkResponse)
@limiter.limit("60/minute")
async def get_benchmarks(request: Request, product_category: str):
    """Get cost benchmarking data for a product category."""
    engine: IntelligenceEngine = request.app.state.engine

    # Get benchmark data
    results = engine.query(
        product=product_category,
        location="35242",  # Default location
        radius_miles=100,
    )

    if not results.benchmark:
        raise HTTPException(
            status_code=404,
            detail=f"No benchmark data available for category: {product_category}",
        )

    return CategoryBenchmarkResponse(
        product_category=product_category,
        benchmark=BenchmarkData(
            industry_average=results.benchmark.industry_average,
            geographic_premium=results.benchmark.geographic_premium,
            percentile_25=results.benchmark.percentile_25,
            percentile_50=results.benchmark.percentile_50,
            percentile_75=results.benchmark.percentile_75,
            unit=results.benchmark.unit,
        ),
        sample_size=results.vendor_count,
        data_freshness_days=7,
        geographic_coverage=["AL", "GA", "TN", "MS", "FL"],
    )


# ============================================
# User Override Logging for RLHF
# ============================================


class UserOverrideLog(BaseModel):
    """Log entry for user override of AI recommendation."""

    sku_id: str
    ai_recommended_value: float
    user_selected_value: float
    promo_type: str
    reason: str | None = None


@app.post("/v1/inference/log-override")
@limiter.limit("60/minute")
async def log_user_override(request: Request, body: UserOverrideLog):
    """Log user override of AI recommendation for RLHF fine-tuning."""
    # In production, this would store to a database for model retraining
    override_rate = abs(body.user_selected_value - body.ai_recommended_value) / body.ai_recommended_value
    return {
        "logged": True,
        "override_rate": override_rate,
        "message": "Override logged for RLHF fine-tuning",
    }
