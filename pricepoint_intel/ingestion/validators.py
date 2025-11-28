"""Data validation module for ingestion pipeline.

Provides comprehensive validation for SKU, pricing, and market data.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"  # Data cannot be imported
    WARNING = "warning"  # Data imported with modifications
    INFO = "info"  # Informational only


@dataclass
class ValidationError:
    """Represents a single validation error."""

    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    value: Any = None
    row_index: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
            "value": str(self.value) if self.value is not None else None,
            "row_index": self.row_index,
        }


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    cleaned_data: Optional[dict] = None
    row_index: Optional[int] = None

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def add_error(
        self,
        field: str,
        message: str,
        value: Any = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> None:
        """Add a validation error."""
        error = ValidationError(
            field=field,
            message=message,
            severity=severity,
            value=value,
            row_index=self.row_index,
        )
        if severity == ValidationSeverity.ERROR:
            self.errors.append(error)
            self.is_valid = False
        else:
            self.warnings.append(error)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "row_index": self.row_index,
        }


class DataValidator:
    """Base validator with common validation methods."""

    # Common regex patterns
    SKU_PATTERN = re.compile(r"^[A-Za-z0-9\-_]{3,50}$")
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    PHONE_PATTERN = re.compile(r"^[\d\-\+\(\)\s]{7,20}$")
    ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")
    CURRENCY_CODES = {"USD", "EUR", "GBP", "CAD", "MXN", "AUD", "JPY", "CNY"}
    VALID_CATEGORIES = {
        "flooring",
        "building_materials",
        "electrical",
        "plumbing",
        "hvac",
        "hardware",
        "lumber",
        "paint",
        "tools",
        "other",
    }

    @staticmethod
    def validate_required(
        value: Any, field_name: str, result: ValidationResult
    ) -> bool:
        """Validate that a required field is present and not empty."""
        if value is None or (isinstance(value, str) and not value.strip()):
            result.add_error(field_name, f"{field_name} is required", value)
            return False
        return True

    @staticmethod
    def validate_string_length(
        value: str,
        field_name: str,
        result: ValidationResult,
        min_length: int = 1,
        max_length: int = 255,
    ) -> bool:
        """Validate string length is within bounds."""
        if value is None:
            return True

        length = len(str(value).strip())
        if length < min_length:
            result.add_error(
                field_name,
                f"{field_name} must be at least {min_length} characters",
                value,
            )
            return False
        if length > max_length:
            result.add_error(
                field_name,
                f"{field_name} must not exceed {max_length} characters",
                value,
            )
            return False
        return True

    @staticmethod
    def validate_numeric(
        value: Any,
        field_name: str,
        result: ValidationResult,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allow_none: bool = True,
    ) -> Optional[float]:
        """Validate and convert numeric value."""
        if value is None or (isinstance(value, str) and not value.strip()):
            if not allow_none:
                result.add_error(field_name, f"{field_name} is required", value)
            return None

        try:
            num_value = float(value)
            if min_value is not None and num_value < min_value:
                result.add_error(
                    field_name,
                    f"{field_name} must be at least {min_value}",
                    value,
                )
                return None
            if max_value is not None and num_value > max_value:
                result.add_error(
                    field_name,
                    f"{field_name} must not exceed {max_value}",
                    value,
                )
                return None
            return num_value
        except (ValueError, TypeError):
            result.add_error(field_name, f"{field_name} must be a valid number", value)
            return None

    @staticmethod
    def validate_integer(
        value: Any,
        field_name: str,
        result: ValidationResult,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        allow_none: bool = True,
    ) -> Optional[int]:
        """Validate and convert integer value."""
        if value is None or (isinstance(value, str) and not value.strip()):
            if not allow_none:
                result.add_error(field_name, f"{field_name} is required", value)
            return None

        try:
            int_value = int(float(value))  # Handle "10.0" format
            if min_value is not None and int_value < min_value:
                result.add_error(
                    field_name,
                    f"{field_name} must be at least {min_value}",
                    value,
                )
                return None
            if max_value is not None and int_value > max_value:
                result.add_error(
                    field_name,
                    f"{field_name} must not exceed {max_value}",
                    value,
                )
                return None
            return int_value
        except (ValueError, TypeError):
            result.add_error(
                field_name, f"{field_name} must be a valid integer", value
            )
            return None

    @staticmethod
    def validate_decimal(
        value: Any,
        field_name: str,
        result: ValidationResult,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        precision: int = 4,
        allow_none: bool = True,
    ) -> Optional[Decimal]:
        """Validate and convert decimal value (for pricing)."""
        if value is None or (isinstance(value, str) and not value.strip()):
            if not allow_none:
                result.add_error(field_name, f"{field_name} is required", value)
            return None

        try:
            # Handle string with currency symbols
            if isinstance(value, str):
                value = value.replace("$", "").replace(",", "").strip()

            dec_value = Decimal(str(value)).quantize(Decimal(f"0.{'0' * precision}"))

            if min_value is not None and dec_value < min_value:
                result.add_error(
                    field_name,
                    f"{field_name} must be at least {min_value}",
                    value,
                )
                return None
            if max_value is not None and dec_value > max_value:
                result.add_error(
                    field_name,
                    f"{field_name} must not exceed {max_value}",
                    value,
                )
                return None
            return dec_value
        except (InvalidOperation, ValueError, TypeError):
            result.add_error(
                field_name, f"{field_name} must be a valid decimal number", value
            )
            return None

    @classmethod
    def validate_pattern(
        cls,
        value: str,
        field_name: str,
        result: ValidationResult,
        pattern: re.Pattern,
        message: str,
    ) -> bool:
        """Validate value against a regex pattern."""
        if value is None:
            return True

        if not pattern.match(str(value)):
            result.add_error(field_name, message, value)
            return False
        return True

    @classmethod
    def validate_enum(
        cls,
        value: str,
        field_name: str,
        result: ValidationResult,
        valid_values: set[str],
        case_sensitive: bool = False,
    ) -> Optional[str]:
        """Validate value is in a set of allowed values."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        check_value = str(value) if case_sensitive else str(value).lower()
        valid_set = valid_values if case_sensitive else {v.lower() for v in valid_values}

        if check_value not in valid_set:
            result.add_error(
                field_name,
                f"{field_name} must be one of: {', '.join(sorted(valid_values))}",
                value,
            )
            return None

        return check_value if not case_sensitive else value

    @staticmethod
    def validate_date(
        value: Any,
        field_name: str,
        result: ValidationResult,
        date_formats: Optional[list[str]] = None,
        allow_none: bool = True,
    ) -> Optional[datetime]:
        """Validate and parse date value."""
        if value is None or (isinstance(value, str) and not value.strip()):
            if not allow_none:
                result.add_error(field_name, f"{field_name} is required", value)
            return None

        # Already a datetime
        if isinstance(value, datetime):
            return value

        # Default formats to try
        if date_formats is None:
            date_formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y",
                "%m/%d/%y",
                "%d-%m-%Y",
            ]

        for fmt in date_formats:
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue

        result.add_error(
            field_name,
            f"{field_name} must be a valid date (expected formats: YYYY-MM-DD, MM/DD/YYYY)",
            value,
        )
        return None

    @classmethod
    def validate_coordinates(
        cls,
        latitude: Any,
        longitude: Any,
        result: ValidationResult,
        lat_field: str = "latitude",
        lon_field: str = "longitude",
    ) -> tuple[Optional[float], Optional[float]]:
        """Validate geographic coordinates."""
        lat = cls.validate_numeric(
            latitude, lat_field, result, min_value=-90, max_value=90, allow_none=False
        )
        lon = cls.validate_numeric(
            longitude, lon_field, result, min_value=-180, max_value=180, allow_none=False
        )
        return lat, lon


class SKUValidator(DataValidator):
    """Validator for SKU data."""

    REQUIRED_FIELDS = {"sku_id", "product_name", "category"}
    OPTIONAL_FIELDS = {
        "description",
        "subcategory",
        "weight_lbs",
        "length_inches",
        "width_inches",
        "height_inches",
        "unit_of_measure",
        "units_per_case",
        "primary_supplier_id",
        "manufacturer",
        "manufacturer_part_number",
        "upc_code",
    }

    def validate(self, data: dict, row_index: Optional[int] = None) -> ValidationResult:
        """Validate SKU data.

        Args:
            data: Dictionary containing SKU data
            row_index: Optional row index for error reporting

        Returns:
            ValidationResult with validation status and cleaned data
        """
        result = ValidationResult(is_valid=True, row_index=row_index)
        cleaned = {}

        # Required fields
        if self.validate_required(data.get("sku_id"), "sku_id", result):
            sku_id = str(data["sku_id"]).strip().upper()
            if self.validate_pattern(
                sku_id,
                "sku_id",
                result,
                self.SKU_PATTERN,
                "sku_id must be 3-50 alphanumeric characters with hyphens/underscores",
            ):
                cleaned["sku_id"] = sku_id

        if self.validate_required(data.get("product_name"), "product_name", result):
            if self.validate_string_length(
                data["product_name"], "product_name", result, min_length=2, max_length=255
            ):
                cleaned["product_name"] = str(data["product_name"]).strip()

        if self.validate_required(data.get("category"), "category", result):
            category = self.validate_enum(
                data["category"], "category", result, self.VALID_CATEGORIES
            )
            if category:
                cleaned["category"] = category

        # Optional fields
        if data.get("description"):
            cleaned["description"] = str(data["description"]).strip()[:2000]

        if data.get("subcategory"):
            if self.validate_string_length(
                data["subcategory"], "subcategory", result, max_length=100
            ):
                cleaned["subcategory"] = str(data["subcategory"]).strip()

        # Dimensions
        for dim_field in ["weight_lbs", "length_inches", "width_inches", "height_inches"]:
            if data.get(dim_field) is not None:
                value = self.validate_numeric(
                    data[dim_field], dim_field, result, min_value=0, max_value=10000
                )
                if value is not None:
                    cleaned[dim_field] = value

        # Unit fields
        if data.get("unit_of_measure"):
            cleaned["unit_of_measure"] = str(data["unit_of_measure"]).strip().lower()
        else:
            cleaned["unit_of_measure"] = "each"

        if data.get("units_per_case") is not None:
            units = self.validate_integer(
                data["units_per_case"], "units_per_case", result, min_value=1
            )
            if units is not None:
                cleaned["units_per_case"] = units

        # Supplier info
        if data.get("primary_supplier_id"):
            cleaned["primary_supplier_id"] = str(data["primary_supplier_id"]).strip()

        if data.get("manufacturer"):
            cleaned["manufacturer"] = str(data["manufacturer"]).strip()[:255]

        if data.get("manufacturer_part_number"):
            cleaned["manufacturer_part_number"] = str(
                data["manufacturer_part_number"]
            ).strip()[:100]

        if data.get("upc_code"):
            upc = str(data["upc_code"]).strip()
            if len(upc) in [8, 12, 13, 14]:  # Valid UPC lengths
                cleaned["upc_code"] = upc
            else:
                result.add_error(
                    "upc_code",
                    "UPC code must be 8, 12, 13, or 14 digits",
                    upc,
                    severity=ValidationSeverity.WARNING,
                )

        result.cleaned_data = cleaned
        return result


class PricingValidator(DataValidator):
    """Validator for vendor pricing data."""

    REQUIRED_FIELDS = {"sku_id", "vendor_id", "price"}
    OPTIONAL_FIELDS = {
        "currency",
        "price_per_unit",
        "unit_of_measure",
        "geographic_region",
        "effective_date",
        "expiration_date",
        "confidence_score",
        "data_source",
        "volume_pricing",
    }

    def validate(self, data: dict, row_index: Optional[int] = None) -> ValidationResult:
        """Validate pricing data.

        Args:
            data: Dictionary containing pricing data
            row_index: Optional row index for error reporting

        Returns:
            ValidationResult with validation status and cleaned data
        """
        result = ValidationResult(is_valid=True, row_index=row_index)
        cleaned = {}

        # Required fields
        if self.validate_required(data.get("sku_id"), "sku_id", result):
            cleaned["sku_id"] = str(data["sku_id"]).strip().upper()

        if self.validate_required(data.get("vendor_id"), "vendor_id", result):
            cleaned["vendor_id"] = str(data["vendor_id"]).strip()

        if self.validate_required(data.get("price"), "price", result):
            price = self.validate_decimal(
                data["price"],
                "price",
                result,
                min_value=Decimal("0.0001"),
                max_value=Decimal("999999999.9999"),
                allow_none=False,
            )
            if price is not None:
                cleaned["price"] = float(price)

        # Currency
        currency = self.validate_enum(
            data.get("currency", "USD"),
            "currency",
            result,
            self.CURRENCY_CODES,
            case_sensitive=True,
        )
        cleaned["currency"] = currency.upper() if currency else "USD"

        # Optional price per unit
        if data.get("price_per_unit") is not None:
            ppu = self.validate_decimal(
                data["price_per_unit"],
                "price_per_unit",
                result,
                min_value=Decimal("0"),
            )
            if ppu is not None:
                cleaned["price_per_unit"] = float(ppu)

        # Unit of measure
        if data.get("unit_of_measure"):
            cleaned["unit_of_measure"] = str(data["unit_of_measure"]).strip().lower()
        else:
            cleaned["unit_of_measure"] = "each"

        # Geographic region
        if data.get("geographic_region"):
            if self.validate_string_length(
                data["geographic_region"], "geographic_region", result, max_length=100
            ):
                cleaned["geographic_region"] = str(data["geographic_region"]).strip()

        # Dates
        if data.get("effective_date"):
            eff_date = self.validate_date(data["effective_date"], "effective_date", result)
            if eff_date:
                cleaned["effective_date"] = eff_date

        if data.get("expiration_date"):
            exp_date = self.validate_date(data["expiration_date"], "expiration_date", result)
            if exp_date:
                cleaned["expiration_date"] = exp_date

        # Validate date logic
        if cleaned.get("effective_date") and cleaned.get("expiration_date"):
            if cleaned["expiration_date"] < cleaned["effective_date"]:
                result.add_error(
                    "expiration_date",
                    "Expiration date must be after effective date",
                    data.get("expiration_date"),
                )

        # Confidence score
        if data.get("confidence_score") is not None:
            conf = self.validate_numeric(
                data["confidence_score"],
                "confidence_score",
                result,
                min_value=0,
                max_value=1,
            )
            if conf is not None:
                cleaned["confidence_score"] = conf

        # Data source
        if data.get("data_source"):
            cleaned["data_source"] = str(data["data_source"]).strip()[:100]

        # Volume pricing (JSON)
        if data.get("volume_pricing"):
            if isinstance(data["volume_pricing"], dict):
                cleaned["volume_pricing"] = data["volume_pricing"]
            elif isinstance(data["volume_pricing"], str):
                try:
                    import json
                    cleaned["volume_pricing"] = json.loads(data["volume_pricing"])
                except json.JSONDecodeError:
                    result.add_error(
                        "volume_pricing",
                        "volume_pricing must be valid JSON",
                        data["volume_pricing"],
                        severity=ValidationSeverity.WARNING,
                    )

        result.cleaned_data = cleaned
        return result


class MarketValidator(DataValidator):
    """Validator for geographic market data."""

    REQUIRED_FIELDS = {"market_id", "region_name", "latitude", "longitude"}
    OPTIONAL_FIELDS = {
        "region_code",
        "country_code",
        "market_size_tier",
        "population",
        "gdp_per_capita",
        "cost_of_living_index",
        "regional_price_multiplier",
        "bbox_north",
        "bbox_south",
        "bbox_east",
        "bbox_west",
    }
    VALID_TIERS = {"tier_1", "tier_2", "tier_3", "tier_4"}

    def validate(self, data: dict, row_index: Optional[int] = None) -> ValidationResult:
        """Validate geographic market data.

        Args:
            data: Dictionary containing market data
            row_index: Optional row index for error reporting

        Returns:
            ValidationResult with validation status and cleaned data
        """
        result = ValidationResult(is_valid=True, row_index=row_index)
        cleaned = {}

        # Required fields
        if self.validate_required(data.get("market_id"), "market_id", result):
            cleaned["market_id"] = str(data["market_id"]).strip()

        if self.validate_required(data.get("region_name"), "region_name", result):
            if self.validate_string_length(
                data["region_name"], "region_name", result, max_length=255
            ):
                cleaned["region_name"] = str(data["region_name"]).strip()

        # Coordinates
        lat, lon = self.validate_coordinates(
            data.get("latitude"), data.get("longitude"), result
        )
        if lat is not None:
            cleaned["latitude"] = lat
        if lon is not None:
            cleaned["longitude"] = lon

        # Optional fields
        if data.get("region_code"):
            cleaned["region_code"] = str(data["region_code"]).strip()[:20]

        if data.get("country_code"):
            country = str(data["country_code"]).strip().upper()
            if len(country) <= 3:
                cleaned["country_code"] = country
        else:
            cleaned["country_code"] = "USA"

        # Market tier
        if data.get("market_size_tier"):
            tier = self.validate_enum(
                data["market_size_tier"],
                "market_size_tier",
                result,
                self.VALID_TIERS,
            )
            if tier:
                cleaned["market_size_tier"] = tier
        else:
            cleaned["market_size_tier"] = "tier_3"

        # Population
        if data.get("population") is not None:
            pop = self.validate_integer(
                data["population"], "population", result, min_value=0
            )
            if pop is not None:
                cleaned["population"] = pop

        # GDP per capita
        if data.get("gdp_per_capita") is not None:
            gdp = self.validate_numeric(
                data["gdp_per_capita"], "gdp_per_capita", result, min_value=0
            )
            if gdp is not None:
                cleaned["gdp_per_capita"] = gdp

        # Cost indices
        if data.get("cost_of_living_index") is not None:
            coli = self.validate_numeric(
                data["cost_of_living_index"],
                "cost_of_living_index",
                result,
                min_value=0.1,
                max_value=5.0,
            )
            if coli is not None:
                cleaned["cost_of_living_index"] = coli
        else:
            cleaned["cost_of_living_index"] = 1.0

        if data.get("regional_price_multiplier") is not None:
            rpm = self.validate_numeric(
                data["regional_price_multiplier"],
                "regional_price_multiplier",
                result,
                min_value=0.1,
                max_value=5.0,
            )
            if rpm is not None:
                cleaned["regional_price_multiplier"] = rpm
        else:
            cleaned["regional_price_multiplier"] = 1.0

        # Bounding box
        for bbox_field in ["bbox_north", "bbox_south", "bbox_east", "bbox_west"]:
            if data.get(bbox_field) is not None:
                min_val = -180 if "east" in bbox_field or "west" in bbox_field else -90
                max_val = 180 if "east" in bbox_field or "west" in bbox_field else 90
                val = self.validate_numeric(
                    data[bbox_field], bbox_field, result, min_value=min_val, max_value=max_val
                )
                if val is not None:
                    cleaned[bbox_field] = val

        result.cleaned_data = cleaned
        return result


class VendorValidator(DataValidator):
    """Validator for vendor data."""

    REQUIRED_FIELDS = {"vendor_id", "vendor_name"}
    OPTIONAL_FIELDS = {
        "vendor_type",
        "contact_email",
        "contact_phone",
        "website",
        "headquarters_address",
        "headquarters_city",
        "headquarters_state",
        "headquarters_country",
        "headquarters_zip",
        "latitude",
        "longitude",
        "reliability_score",
        "avg_lead_time_days",
        "min_order_value",
        "api_enabled",
        "api_endpoint",
    }
    VALID_VENDOR_TYPES = {"distributor", "manufacturer", "retailer", "wholesaler", "other"}

    def validate(self, data: dict, row_index: Optional[int] = None) -> ValidationResult:
        """Validate vendor data.

        Args:
            data: Dictionary containing vendor data
            row_index: Optional row index for error reporting

        Returns:
            ValidationResult with validation status and cleaned data
        """
        result = ValidationResult(is_valid=True, row_index=row_index)
        cleaned = {}

        # Required fields
        if self.validate_required(data.get("vendor_id"), "vendor_id", result):
            cleaned["vendor_id"] = str(data["vendor_id"]).strip()

        if self.validate_required(data.get("vendor_name"), "vendor_name", result):
            if self.validate_string_length(
                data["vendor_name"], "vendor_name", result, max_length=255
            ):
                cleaned["vendor_name"] = str(data["vendor_name"]).strip()

        # Vendor type
        if data.get("vendor_type"):
            v_type = self.validate_enum(
                data["vendor_type"],
                "vendor_type",
                result,
                self.VALID_VENDOR_TYPES,
            )
            if v_type:
                cleaned["vendor_type"] = v_type

        # Contact info
        if data.get("contact_email"):
            email = str(data["contact_email"]).strip().lower()
            if self.validate_pattern(
                email,
                "contact_email",
                result,
                self.EMAIL_PATTERN,
                "Invalid email format",
            ):
                cleaned["contact_email"] = email

        if data.get("contact_phone"):
            cleaned["contact_phone"] = str(data["contact_phone"]).strip()

        if data.get("website"):
            cleaned["website"] = str(data["website"]).strip()[:500]

        # Address fields
        for addr_field in [
            "headquarters_address",
            "headquarters_city",
            "headquarters_state",
        ]:
            if data.get(addr_field):
                cleaned[addr_field] = str(data[addr_field]).strip()

        if data.get("headquarters_country"):
            cleaned["headquarters_country"] = str(
                data["headquarters_country"]
            ).strip().upper()[:3]
        else:
            cleaned["headquarters_country"] = "USA"

        if data.get("headquarters_zip"):
            zip_code = str(data["headquarters_zip"]).strip()
            if self.validate_pattern(
                zip_code,
                "headquarters_zip",
                result,
                self.ZIP_PATTERN,
                "Invalid ZIP code format (expected: 12345 or 12345-6789)",
            ):
                cleaned["headquarters_zip"] = zip_code

        # Coordinates
        if data.get("latitude") is not None or data.get("longitude") is not None:
            lat, lon = self.validate_coordinates(
                data.get("latitude"), data.get("longitude"), result
            )
            if lat is not None:
                cleaned["latitude"] = lat
            if lon is not None:
                cleaned["longitude"] = lon

        # Metrics
        if data.get("reliability_score") is not None:
            rel = self.validate_numeric(
                data["reliability_score"],
                "reliability_score",
                result,
                min_value=0,
                max_value=1,
            )
            if rel is not None:
                cleaned["reliability_score"] = rel

        if data.get("avg_lead_time_days") is not None:
            lead = self.validate_integer(
                data["avg_lead_time_days"],
                "avg_lead_time_days",
                result,
                min_value=0,
                max_value=365,
            )
            if lead is not None:
                cleaned["avg_lead_time_days"] = lead

        if data.get("min_order_value") is not None:
            mov = self.validate_numeric(
                data["min_order_value"], "min_order_value", result, min_value=0
            )
            if mov is not None:
                cleaned["min_order_value"] = mov

        # API settings
        cleaned["api_enabled"] = bool(data.get("api_enabled", False))
        if data.get("api_endpoint"):
            cleaned["api_endpoint"] = str(data["api_endpoint"]).strip()[:500]

        result.cleaned_data = cleaned
        return result
