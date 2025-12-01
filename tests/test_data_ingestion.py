"""Unit tests for the data ingestion pipeline.

Tests data validation, CSV/Excel import, and API connector functionality.
"""

import io
import json
import pytest
from datetime import datetime
from decimal import Decimal

from pricepoint_intel.ingestion.validators import (
    DataValidator,
    SKUValidator,
    PricingValidator,
    MarketValidator,
    VendorValidator,
    ValidationResult,
    ValidationSeverity,
)


class TestDataValidator:
    """Tests for base DataValidator class."""

    def test_validate_required_with_value(self):
        """Test required field validation with valid value."""
        result = ValidationResult(is_valid=True)
        valid = DataValidator.validate_required("test_value", "field_name", result)
        assert valid is True
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_required_with_none(self):
        """Test required field validation with None."""
        result = ValidationResult(is_valid=True)
        valid = DataValidator.validate_required(None, "field_name", result)
        assert valid is False
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "field_name"

    def test_validate_required_with_empty_string(self):
        """Test required field validation with empty string."""
        result = ValidationResult(is_valid=True)
        valid = DataValidator.validate_required("   ", "field_name", result)
        assert valid is False
        assert result.is_valid is False

    def test_validate_string_length_valid(self):
        """Test string length validation with valid length."""
        result = ValidationResult(is_valid=True)
        valid = DataValidator.validate_string_length(
            "test", "field_name", result, min_length=2, max_length=10
        )
        assert valid is True
        assert result.is_valid is True

    def test_validate_string_length_too_short(self):
        """Test string length validation with too short value."""
        result = ValidationResult(is_valid=True)
        valid = DataValidator.validate_string_length(
            "a", "field_name", result, min_length=2, max_length=10
        )
        assert valid is False
        assert result.is_valid is False
        assert "at least 2 characters" in result.errors[0].message

    def test_validate_string_length_too_long(self):
        """Test string length validation with too long value."""
        result = ValidationResult(is_valid=True)
        valid = DataValidator.validate_string_length(
            "this is a very long string", "field_name", result, max_length=10
        )
        assert valid is False
        assert "must not exceed 10 characters" in result.errors[0].message

    def test_validate_numeric_valid(self):
        """Test numeric validation with valid value."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_numeric(
            "42.5", "field_name", result, min_value=0, max_value=100
        )
        assert value == 42.5
        assert result.is_valid is True

    def test_validate_numeric_invalid(self):
        """Test numeric validation with invalid value."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_numeric("not_a_number", "field_name", result)
        assert value is None
        assert result.is_valid is False

    def test_validate_numeric_below_min(self):
        """Test numeric validation with value below minimum."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_numeric(
            "-5", "field_name", result, min_value=0
        )
        assert value is None
        assert result.is_valid is False
        assert "at least 0" in result.errors[0].message

    def test_validate_numeric_above_max(self):
        """Test numeric validation with value above maximum."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_numeric(
            "150", "field_name", result, max_value=100
        )
        assert value is None
        assert "must not exceed 100" in result.errors[0].message

    def test_validate_integer_valid(self):
        """Test integer validation with valid value."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_integer("42", "field_name", result)
        assert value == 42
        assert isinstance(value, int)

    def test_validate_integer_from_float(self):
        """Test integer validation converts floats."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_integer("42.0", "field_name", result)
        assert value == 42
        assert isinstance(value, int)

    def test_validate_decimal_valid(self):
        """Test decimal validation with valid value."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_decimal("99.99", "field_name", result)
        assert value == Decimal("99.9900")

    def test_validate_decimal_with_currency_symbol(self):
        """Test decimal validation strips currency symbols."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_decimal("$1,234.56", "field_name", result)
        assert value == Decimal("1234.5600")

    def test_validate_enum_valid(self):
        """Test enum validation with valid value."""
        result = ValidationResult(is_valid=True)
        valid_values = {"red", "green", "blue"}
        value = DataValidator.validate_enum(
            "GREEN", "field_name", result, valid_values
        )
        assert value == "green"

    def test_validate_enum_invalid(self):
        """Test enum validation with invalid value."""
        result = ValidationResult(is_valid=True)
        valid_values = {"red", "green", "blue"}
        value = DataValidator.validate_enum(
            "purple", "field_name", result, valid_values
        )
        assert value is None
        assert result.is_valid is False

    def test_validate_date_iso_format(self):
        """Test date validation with ISO format."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_date("2024-01-15", "field_name", result)
        assert value is not None
        assert value.year == 2024
        assert value.month == 1
        assert value.day == 15

    def test_validate_date_us_format(self):
        """Test date validation with US format."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_date("01/15/2024", "field_name", result)
        assert value is not None
        assert value.year == 2024

    def test_validate_date_invalid(self):
        """Test date validation with invalid format."""
        result = ValidationResult(is_valid=True)
        value = DataValidator.validate_date("invalid_date", "field_name", result)
        assert value is None
        assert result.is_valid is False

    def test_validate_coordinates_valid(self):
        """Test coordinate validation with valid values."""
        result = ValidationResult(is_valid=True)
        lat, lon = DataValidator.validate_coordinates(40.7128, -74.0060, result)
        assert lat == 40.7128
        assert lon == -74.0060

    def test_validate_coordinates_invalid_latitude(self):
        """Test coordinate validation with invalid latitude."""
        result = ValidationResult(is_valid=True)
        lat, lon = DataValidator.validate_coordinates(91.0, -74.0, result)
        assert lat is None
        assert result.is_valid is False

    def test_validate_coordinates_invalid_longitude(self):
        """Test coordinate validation with invalid longitude."""
        result = ValidationResult(is_valid=True)
        lat, lon = DataValidator.validate_coordinates(40.0, 181.0, result)
        assert lon is None


class TestSKUValidator:
    """Tests for SKU data validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SKUValidator()

    def test_validate_valid_sku(self):
        """Test validation of valid SKU data."""
        data = {
            "sku_id": "SKU-001",
            "product_name": "Oak Hardwood Flooring",
            "category": "flooring",
            "weight_lbs": 25.5,
            "manufacturer": "FloorCo Inc",
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["sku_id"] == "SKU-001"
        assert result.cleaned_data["category"] == "flooring"

    def test_validate_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        data = {
            "sku_id": "SKU-001",
            # Missing product_name and category
        }
        result = self.validator.validate(data)
        assert result.is_valid is False
        assert len(result.errors) >= 2

    def test_validate_invalid_sku_id_pattern(self):
        """Test validation fails with invalid SKU ID pattern."""
        data = {
            "sku_id": "ab",  # Too short
            "product_name": "Test Product",
            "category": "flooring",
        }
        result = self.validator.validate(data)
        assert result.is_valid is False
        assert any("sku_id" in e.field for e in result.errors)

    def test_validate_invalid_category(self):
        """Test validation fails with invalid category."""
        data = {
            "sku_id": "SKU-001",
            "product_name": "Test Product",
            "category": "invalid_category",
        }
        result = self.validator.validate(data)
        assert result.is_valid is False
        assert any("category" in e.field for e in result.errors)

    def test_validate_optional_dimensions(self):
        """Test validation handles optional dimensions correctly."""
        data = {
            "sku_id": "SKU-001",
            "product_name": "Test Product",
            "category": "flooring",
            "weight_lbs": "25.5",
            "length_inches": "48",
            "width_inches": "6",
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["weight_lbs"] == 25.5
        assert result.cleaned_data["length_inches"] == 48.0

    def test_validate_upc_code_warning(self):
        """Test validation warns on invalid UPC length."""
        data = {
            "sku_id": "SKU-001",
            "product_name": "Test Product",
            "category": "flooring",
            "upc_code": "123",  # Invalid length
        }
        result = self.validator.validate(data)
        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) >= 1


class TestPricingValidator:
    """Tests for pricing data validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PricingValidator()

    def test_validate_valid_pricing(self):
        """Test validation of valid pricing data."""
        data = {
            "sku_id": "SKU-001",
            "vendor_id": "VENDOR-001",
            "price": "99.99",
            "currency": "USD",
            "geographic_region": "Northeast",
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["price"] == 99.99
        assert result.cleaned_data["currency"] == "USD"

    def test_validate_missing_price(self):
        """Test validation fails with missing price."""
        data = {
            "sku_id": "SKU-001",
            "vendor_id": "VENDOR-001",
        }
        result = self.validator.validate(data)
        assert result.is_valid is False
        assert any("price" in e.field for e in result.errors)

    def test_validate_invalid_currency(self):
        """Test validation fails with invalid currency code."""
        data = {
            "sku_id": "SKU-001",
            "vendor_id": "VENDOR-001",
            "price": "99.99",
            "currency": "INVALID",
        }
        result = self.validator.validate(data)
        assert result.is_valid is False

    def test_validate_price_with_currency_symbol(self):
        """Test validation strips currency symbols from price."""
        data = {
            "sku_id": "SKU-001",
            "vendor_id": "VENDOR-001",
            "price": "$1,234.56",
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["price"] == 1234.56

    def test_validate_date_range(self):
        """Test validation fails when expiration is before effective date."""
        data = {
            "sku_id": "SKU-001",
            "vendor_id": "VENDOR-001",
            "price": "99.99",
            "effective_date": "2024-12-01",
            "expiration_date": "2024-01-01",  # Before effective
        }
        result = self.validator.validate(data)
        assert result.is_valid is False
        assert any("expiration_date" in e.field for e in result.errors)

    def test_validate_confidence_score_range(self):
        """Test confidence score must be between 0 and 1."""
        data = {
            "sku_id": "SKU-001",
            "vendor_id": "VENDOR-001",
            "price": "99.99",
            "confidence_score": "1.5",  # Invalid
        }
        result = self.validator.validate(data)
        assert result.is_valid is False

    def test_validate_volume_pricing_json(self):
        """Test volume pricing accepts valid JSON."""
        data = {
            "sku_id": "SKU-001",
            "vendor_id": "VENDOR-001",
            "price": "99.99",
            "volume_pricing": '{"100": 95.99, "1000": 89.99}',
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["volume_pricing"] == {"100": 95.99, "1000": 89.99}


class TestMarketValidator:
    """Tests for geographic market data validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = MarketValidator()

    def test_validate_valid_market(self):
        """Test validation of valid market data."""
        data = {
            "market_id": "MARKET-NE-001",
            "region_name": "Northeast",
            "latitude": "40.7128",
            "longitude": "-74.0060",
            "market_size_tier": "tier_1",
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["latitude"] == 40.7128
        assert result.cleaned_data["longitude"] == -74.0060

    def test_validate_missing_coordinates(self):
        """Test validation fails with missing coordinates."""
        data = {
            "market_id": "MARKET-001",
            "region_name": "Test Region",
        }
        result = self.validator.validate(data)
        assert result.is_valid is False
        assert any("latitude" in e.field or "longitude" in e.field for e in result.errors)

    def test_validate_invalid_coordinates(self):
        """Test validation fails with invalid coordinates."""
        data = {
            "market_id": "MARKET-001",
            "region_name": "Test Region",
            "latitude": "91",  # Invalid
            "longitude": "-74",
        }
        result = self.validator.validate(data)
        assert result.is_valid is False

    def test_validate_cost_index_defaults(self):
        """Test cost indices default to 1.0."""
        data = {
            "market_id": "MARKET-001",
            "region_name": "Test Region",
            "latitude": "40",
            "longitude": "-74",
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["cost_of_living_index"] == 1.0
        assert result.cleaned_data["regional_price_multiplier"] == 1.0


class TestVendorValidator:
    """Tests for vendor data validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = VendorValidator()

    def test_validate_valid_vendor(self):
        """Test validation of valid vendor data."""
        data = {
            "vendor_id": "VENDOR-001",
            "vendor_name": "ABC Supply Co",
            "vendor_type": "distributor",
            "contact_email": "sales@abc.com",
            "headquarters_city": "New York",
            "headquarters_state": "NY",
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["vendor_type"] == "distributor"

    def test_validate_invalid_email(self):
        """Test validation fails with invalid email."""
        data = {
            "vendor_id": "VENDOR-001",
            "vendor_name": "ABC Supply Co",
            "contact_email": "invalid-email",
        }
        result = self.validator.validate(data)
        assert result.is_valid is False
        assert any("email" in e.field for e in result.errors)

    def test_validate_reliability_score_range(self):
        """Test reliability score must be between 0 and 1."""
        data = {
            "vendor_id": "VENDOR-001",
            "vendor_name": "ABC Supply Co",
            "reliability_score": "0.85",
        }
        result = self.validator.validate(data)
        assert result.is_valid is True
        assert result.cleaned_data["reliability_score"] == 0.85

    def test_validate_invalid_reliability_score(self):
        """Test validation fails with invalid reliability score."""
        data = {
            "vendor_id": "VENDOR-001",
            "vendor_name": "ABC Supply Co",
            "reliability_score": "1.5",  # Invalid
        }
        result = self.validator.validate(data)
        assert result.is_valid is False


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_merge_results(self):
        """Test merging two validation results."""
        result1 = ValidationResult(is_valid=True)
        result1.add_error("field1", "Error 1")

        result2 = ValidationResult(is_valid=True)
        result2.add_error("field2", "Error 2")

        result1.merge(result2)
        assert result1.is_valid is False
        assert len(result1.errors) == 2

    def test_warning_does_not_invalidate(self):
        """Test that warnings don't invalidate the result."""
        result = ValidationResult(is_valid=True)
        result.add_error("field", "Warning", severity=ValidationSeverity.WARNING)
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert len(result.errors) == 0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = ValidationResult(is_valid=False, row_index=5)
        result.add_error("field", "Error message", value="bad_value")

        d = result.to_dict()
        assert d["is_valid"] is False
        assert d["error_count"] == 1
        assert d["row_index"] == 5
        assert len(d["errors"]) == 1
