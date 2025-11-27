"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_vendor_data():
    """Sample vendor data for testing."""
    return [
        {
            "vendor_id": "V001",
            "vendor_name": "Test Vendor 1",
            "price_per_unit": 2.50,
            "unit": "sqft",
            "distance_miles": 5.0,
            "last_updated": "2024-01-15",
            "confidence_score": 0.95,
        },
        {
            "vendor_id": "V002",
            "vendor_name": "Test Vendor 2",
            "price_per_unit": 3.00,
            "unit": "sqft",
            "distance_miles": 10.0,
            "last_updated": "2024-01-14",
            "confidence_score": 0.90,
        },
        {
            "vendor_id": "V003",
            "vendor_name": "Test Vendor 3",
            "price_per_unit": 2.75,
            "unit": "sqft",
            "distance_miles": 15.0,
            "last_updated": "2024-01-13",
            "confidence_score": 0.85,
        },
    ]


@pytest.fixture
def sample_promo_request():
    """Sample promo simulation request data."""
    return {
        "sku_id": "SKU-001",
        "current_price": 2.99,
        "promo_type": "percentage",
        "promo_value": 15.0,
        "location_code": "35242",
        "seasonality_factor": 1.0,
        "inventory_level": 500,
        "competitor_prices": [2.50, 2.75, 3.25],
    }


@pytest.fixture
def sample_query_request():
    """Sample query request data."""
    return {
        "query": "laminate flooring",
        "location": "35242",
        "radius_miles": 50,
        "max_results": 50,
    }
