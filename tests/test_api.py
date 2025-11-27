"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from pricepoint_intel import IntelligenceEngine
from pricepoint_intel.api.app import app
from pricepoint_intel.intelligence_engine.predictive_models import PriceForecaster


@pytest.fixture
def client():
    """Create test client with proper lifespan handling."""
    # Initialize state that would normally be set in lifespan
    app.state.engine = IntelligenceEngine()
    app.state.forecaster = PriceForecaster()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestPromoSimulationEndpoint:
    """Tests for promo simulation endpoint."""

    def test_simulate_promo_percentage(self, client):
        """Test promo simulation with percentage type."""
        response = client.post(
            "/v1/inference/simulate-promo",
            json={
                "sku_id": "SKU-001",
                "current_price": 2.99,
                "promo_type": "percentage",
                "promo_value": 15.0,
                "location_code": "35242",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "projected_lift" in data
        assert "confidence_interval" in data
        assert "ai_recommended_value" in data
        assert "calibration_score" in data
        assert "latency_ms" in data
        assert "model_version" in data

    def test_simulate_promo_volume(self, client):
        """Test promo simulation with volume type."""
        response = client.post(
            "/v1/inference/simulate-promo",
            json={
                "sku_id": "SKU-001",
                "current_price": 2.99,
                "promo_type": "volume",
                "promo_value": 100.0,
                "location_code": "35242",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["projected_lift"] >= 0

    def test_simulate_promo_with_optional_params(self, client):
        """Test promo simulation with optional parameters."""
        response = client.post(
            "/v1/inference/simulate-promo",
            json={
                "sku_id": "SKU-001",
                "current_price": 2.99,
                "promo_type": "percentage",
                "promo_value": 10.0,
                "location_code": "35242",
                "seasonality_factor": 1.2,
                "inventory_level": 500,
                "competitor_prices": [2.50, 2.75, 3.25],
            },
        )

        assert response.status_code == 200

    def test_simulate_promo_invalid_price(self, client):
        """Test promo simulation with invalid price."""
        response = client.post(
            "/v1/inference/simulate-promo",
            json={
                "sku_id": "SKU-001",
                "current_price": -1.0,  # Invalid
                "promo_type": "percentage",
                "promo_value": 10.0,
                "location_code": "35242",
            },
        )

        assert response.status_code == 422  # Validation error


class TestPricingEndpoint:
    """Tests for pricing endpoint."""

    def test_get_pricing(self, client):
        """Test getting pricing for a SKU."""
        response = client.get("/v1/pricing/SKU-001")
        assert response.status_code == 200
        data = response.json()
        assert data["sku_id"] == "SKU-001"
        assert "current_price" in data
        assert "vendor_name" in data


class TestQueryEndpoint:
    """Tests for query endpoint."""

    def test_query_intelligence(self, client):
        """Test natural language intelligence query."""
        response = client.post(
            "/v1/query",
            json={
                "query": "laminate flooring",
                "location": "35242",
                "radius_miles": 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["product"] == "laminate flooring"
        assert data["vendor_count"] > 0
        assert len(data["vendors"]) > 0

    def test_query_with_defaults(self, client):
        """Test query with default parameters."""
        response = client.post(
            "/v1/query",
            json={"query": "flooring"},
        )

        assert response.status_code == 200


class TestVendorDiscoveryEndpoint:
    """Tests for vendor discovery endpoint."""

    def test_discover_vendors(self, client):
        """Test vendor discovery by location."""
        response = client.get("/v1/vendors/35242")
        assert response.status_code == 200
        data = response.json()
        assert data["location"] == "35242"
        assert "vendors" in data
        assert data["total_count"] > 0

    def test_discover_vendors_pagination(self, client):
        """Test vendor discovery with pagination."""
        response = client.get("/v1/vendors/35242?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["vendors"]) <= 10


class TestBenchmarksEndpoint:
    """Tests for benchmarks endpoint."""

    def test_get_benchmarks(self, client):
        """Test getting benchmarks for a category."""
        response = client.get("/v1/benchmarks/laminate%20flooring")
        assert response.status_code == 200
        data = response.json()
        assert data["product_category"] == "laminate flooring"
        assert "benchmark" in data
        assert data["benchmark"]["industry_average"] > 0


class TestUserOverrideLogging:
    """Tests for user override logging endpoint."""

    def test_log_override(self, client):
        """Test logging user override."""
        response = client.post(
            "/v1/inference/log-override",
            json={
                "sku_id": "SKU-001",
                "ai_recommended_value": 15.0,
                "user_selected_value": 20.0,
                "promo_type": "percentage",
                "reason": "User prefers higher discount",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["logged"] is True
        assert "override_rate" in data
