"""API connector for real-time pricing feeds.

Provides a flexible connector for integrating with vendor pricing APIs.
Supports JSON endpoints with authentication and rate limiting.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import logging

import httpx
import structlog

from pricepoint_intel.database.models import VendorPricing, Vendor, SKU, PriceHistory
from pricepoint_intel.database.connection import session_scope, DatabaseConfig
from pricepoint_intel.ingestion.validators import PricingValidator, ValidationResult

logger = structlog.get_logger(__name__)


class AuthType(str, Enum):
    """API authentication types."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class APIConnectorConfig:
    """Configuration for API connector.

    Attributes:
        base_url: Base URL for the API
        auth_type: Authentication type
        api_key: API key (if auth_type is API_KEY)
        api_key_header: Header name for API key
        bearer_token: Bearer token (if auth_type is BEARER_TOKEN)
        basic_auth: Tuple of (username, password) for basic auth
        oauth2_config: OAuth2 configuration dict
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)
        rate_limit_requests: Max requests per rate_limit_window
        rate_limit_window: Window size in seconds for rate limiting
        rate_limit_strategy: Rate limiting strategy to use
        verify_ssl: Whether to verify SSL certificates
        custom_headers: Additional headers to include in requests
        response_mapping: Mapping of API response fields to internal fields
    """

    base_url: str
    auth_type: AuthType = AuthType.NONE
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    bearer_token: Optional[str] = None
    basic_auth: Optional[tuple[str, str]] = None
    oauth2_config: Optional[dict] = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    rate_limit_strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW
    verify_ssl: bool = True
    custom_headers: dict = field(default_factory=dict)
    response_mapping: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.auth_type == AuthType.API_KEY and not self.api_key:
            raise ValueError("api_key is required when auth_type is API_KEY")
        if self.auth_type == AuthType.BEARER_TOKEN and not self.bearer_token:
            raise ValueError("bearer_token is required when auth_type is BEARER_TOKEN")
        if self.auth_type == AuthType.BASIC_AUTH and not self.basic_auth:
            raise ValueError("basic_auth is required when auth_type is BASIC_AUTH")


@dataclass
class APIResponse:
    """Structured response from API call."""

    success: bool
    data: Optional[dict | list] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: float = 0.0
    rate_limit_remaining: Optional[int] = None
    retry_after: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "rate_limit_remaining": self.rate_limit_remaining,
        }


@dataclass
class FetchStats:
    """Statistics from API fetch operations."""

    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    records_fetched: int = 0
    records_saved: int = 0
    rate_limited: int = 0
    retries: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: list = field(default_factory=list)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "records_fetched": self.records_fetched,
            "records_saved": self.records_saved,
            "rate_limited": self.rate_limited,
            "retries": self.retries,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors[:50],
        }


class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.strategy = strategy
        self.requests: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Acquire permission to make a request.

        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()

            if self.strategy == RateLimitStrategy.FIXED_WINDOW:
                # Remove old requests outside window
                window_start = now - self.window_seconds
                self.requests = [t for t in self.requests if t > window_start]

                if len(self.requests) >= self.max_requests:
                    return False

                self.requests.append(now)
                return True

            elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
                # Same as fixed window for simplicity
                window_start = now - self.window_seconds
                self.requests = [t for t in self.requests if t > window_start]

                if len(self.requests) >= self.max_requests:
                    return False

                self.requests.append(now)
                return True

            return True

    async def wait_if_needed(self) -> float:
        """Wait if rate limited, returns seconds waited.

        Returns:
            Number of seconds waited
        """
        while not await self.acquire():
            # Calculate wait time
            oldest_request = min(self.requests) if self.requests else time.time()
            wait_time = self.window_seconds - (time.time() - oldest_request) + 0.1
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return wait_time
        return 0.0

    def remaining(self) -> int:
        """Get number of requests remaining in current window."""
        now = time.time()
        window_start = now - self.window_seconds
        current_requests = len([t for t in self.requests if t > window_start])
        return max(0, self.max_requests - current_requests)


class PricingAPIConnector:
    """Connector for vendor pricing APIs.

    Provides methods for fetching real-time pricing data from vendor APIs.
    Supports authentication, rate limiting, retries, and data validation.
    """

    def __init__(
        self,
        config: APIConnectorConfig,
        db_config: Optional[DatabaseConfig] = None,
    ):
        """Initialize API connector.

        Args:
            config: API configuration
            db_config: Database configuration
        """
        self.config = config
        self.db_config = db_config
        self.validator = PricingValidator()
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_requests,
            window_seconds=config.rate_limit_window,
            strategy=config.rate_limit_strategy,
        )
        self._client: Optional[httpx.AsyncClient] = None

    def _get_headers(self) -> dict:
        """Build request headers with authentication."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "PricePoint-Intel/1.0",
            **self.config.custom_headers,
        }

        if self.config.auth_type == AuthType.API_KEY:
            headers[self.config.api_key_header] = self.config.api_key
        elif self.config.auth_type == AuthType.BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {self.config.bearer_token}"

        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            auth = None
            if self.config.auth_type == AuthType.BASIC_AUTH:
                auth = httpx.BasicAuth(*self.config.basic_auth)

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=self._get_headers(),
                auth=auth,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> APIResponse:
        """Make an HTTP request with retries and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body for POST/PUT

        Returns:
            APIResponse with result or error
        """
        # Wait for rate limit
        await self.rate_limiter.wait_if_needed()

        client = await self._get_client()
        start_time = time.time()

        for attempt in range(self.config.max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = await client.get(endpoint, params=params)
                elif method.upper() == "POST":
                    response = await client.post(endpoint, json=data, params=params)
                elif method.upper() == "PUT":
                    response = await client.put(endpoint, json=data, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response_time = (time.time() - start_time) * 1000

                # Check for rate limiting response
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    return APIResponse(
                        success=False,
                        error="Rate limited",
                        status_code=429,
                        response_time_ms=response_time,
                        retry_after=retry_after,
                    )

                # Check for errors
                if response.status_code >= 400:
                    return APIResponse(
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text[:200]}",
                        status_code=response.status_code,
                        response_time_ms=response_time,
                    )

                # Parse response
                try:
                    data = response.json()
                except Exception:
                    data = {"raw": response.text}

                # Get rate limit info from headers
                rate_remaining = response.headers.get("X-RateLimit-Remaining")

                return APIResponse(
                    success=True,
                    data=data,
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    rate_limit_remaining=int(rate_remaining) if rate_remaining else None,
                )

            except httpx.TimeoutException:
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2**attempt))
                    continue
                return APIResponse(
                    success=False,
                    error="Request timed out",
                    response_time_ms=(time.time() - start_time) * 1000,
                )

            except httpx.RequestError as e:
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2**attempt))
                    continue
                return APIResponse(
                    success=False,
                    error=f"Request error: {str(e)}",
                    response_time_ms=(time.time() - start_time) * 1000,
                )

        return APIResponse(
            success=False,
            error="Max retries exceeded",
            response_time_ms=(time.time() - start_time) * 1000,
        )

    def _map_response(self, data: dict) -> dict:
        """Map API response fields to internal field names.

        Args:
            data: API response data

        Returns:
            Mapped data dictionary
        """
        if not self.config.response_mapping:
            return data

        mapped = {}
        for internal_field, api_field in self.config.response_mapping.items():
            if isinstance(api_field, str):
                # Simple field mapping
                if api_field in data:
                    mapped[internal_field] = data[api_field]
            elif isinstance(api_field, list):
                # Nested field access (e.g., ["pricing", "current", "value"])
                value = data
                for key in api_field:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        value = None
                        break
                if value is not None:
                    mapped[internal_field] = value

        return mapped

    async def fetch_pricing(
        self,
        endpoint: str = "/pricing",
        sku_ids: Optional[list[str]] = None,
        vendor_id: Optional[str] = None,
        region: Optional[str] = None,
    ) -> APIResponse:
        """Fetch pricing data from API.

        Args:
            endpoint: API endpoint for pricing data
            sku_ids: Optional list of SKU IDs to fetch
            vendor_id: Optional vendor ID filter
            region: Optional region filter

        Returns:
            APIResponse with pricing data
        """
        params = {}
        if sku_ids:
            params["sku_ids"] = ",".join(sku_ids)
        if vendor_id:
            params["vendor_id"] = vendor_id
        if region:
            params["region"] = region

        return await self._make_request("GET", endpoint, params=params)

    async def fetch_and_save_pricing(
        self,
        endpoint: str = "/pricing",
        sku_ids: Optional[list[str]] = None,
        vendor_id: Optional[str] = None,
        region: Optional[str] = None,
        save_history: bool = True,
    ) -> FetchStats:
        """Fetch pricing data and save to database.

        Args:
            endpoint: API endpoint for pricing data
            sku_ids: Optional list of SKU IDs to fetch
            vendor_id: Vendor ID for this feed
            region: Optional region filter
            save_history: Whether to save price history records

        Returns:
            FetchStats with operation results
        """
        stats = FetchStats(start_time=datetime.utcnow())

        response = await self.fetch_pricing(endpoint, sku_ids, vendor_id, region)
        stats.total_requests += 1

        if not response.success:
            stats.failed += 1
            stats.errors.append(response.error)
            if response.status_code == 429:
                stats.rate_limited += 1
            stats.end_time = datetime.utcnow()
            return stats

        stats.successful += 1

        # Process response data
        pricing_data = response.data
        if isinstance(pricing_data, dict):
            # Single item or wrapped in container
            if "items" in pricing_data:
                pricing_data = pricing_data["items"]
            elif "data" in pricing_data:
                pricing_data = pricing_data["data"]
            elif "pricing" in pricing_data:
                pricing_data = pricing_data["pricing"]
            else:
                pricing_data = [pricing_data]

        if not isinstance(pricing_data, list):
            pricing_data = [pricing_data]

        stats.records_fetched = len(pricing_data)

        with session_scope(self.db_config) as session:
            for item in pricing_data:
                # Map response fields
                mapped = self._map_response(item)

                # Add vendor_id if not in response
                if vendor_id and "vendor_id" not in mapped:
                    mapped["vendor_id"] = vendor_id

                # Validate
                result = self.validator.validate(mapped)
                if not result.is_valid:
                    stats.errors.extend([e.to_dict() for e in result.errors])
                    continue

                # Check if SKU exists
                sku_exists = (
                    session.query(SKU.sku_id)
                    .filter(SKU.sku_id == result.cleaned_data["sku_id"])
                    .first()
                )
                if not sku_exists:
                    continue

                # Check if vendor exists
                vendor_exists = (
                    session.query(Vendor.vendor_id)
                    .filter(Vendor.vendor_id == result.cleaned_data["vendor_id"])
                    .first()
                )
                if not vendor_exists:
                    continue

                # Update or create pricing
                existing = (
                    session.query(VendorPricing)
                    .filter(
                        VendorPricing.sku_id == result.cleaned_data["sku_id"],
                        VendorPricing.vendor_id == result.cleaned_data["vendor_id"],
                        VendorPricing.geographic_region
                        == result.cleaned_data.get("geographic_region"),
                    )
                    .first()
                )

                if existing:
                    # Track price change for history
                    old_price = float(existing.price)
                    new_price = result.cleaned_data["price"]

                    for key, value in result.cleaned_data.items():
                        setattr(existing, key, value)
                    existing.data_source = "api"

                    # Save history if price changed
                    if save_history and old_price != new_price:
                        price_change_pct = ((new_price - old_price) / old_price) * 100
                        history = PriceHistory(
                            sku_id=result.cleaned_data["sku_id"],
                            vendor_id=result.cleaned_data["vendor_id"],
                            price=new_price,
                            currency=result.cleaned_data.get("currency", "USD"),
                            geographic_region=result.cleaned_data.get("geographic_region"),
                            price_change_pct=price_change_pct,
                            is_anomaly=abs(price_change_pct) > 20,  # Flag >20% changes
                            data_source="api",
                        )
                        session.add(history)
                else:
                    # Create new pricing record
                    result.cleaned_data["data_source"] = "api"
                    pricing = VendorPricing(**result.cleaned_data)
                    session.add(pricing)

                    # Save initial history
                    if save_history:
                        history = PriceHistory(
                            sku_id=result.cleaned_data["sku_id"],
                            vendor_id=result.cleaned_data["vendor_id"],
                            price=result.cleaned_data["price"],
                            currency=result.cleaned_data.get("currency", "USD"),
                            geographic_region=result.cleaned_data.get("geographic_region"),
                            data_source="api",
                        )
                        session.add(history)

                stats.records_saved += 1

        stats.end_time = datetime.utcnow()
        return stats

    async def fetch_bulk_pricing(
        self,
        endpoint: str = "/pricing/bulk",
        sku_ids: list[str] = None,
        vendor_id: Optional[str] = None,
        batch_size: int = 100,
    ) -> FetchStats:
        """Fetch pricing for multiple SKUs in batches.

        Args:
            endpoint: API endpoint for bulk pricing
            sku_ids: List of SKU IDs to fetch
            vendor_id: Vendor ID for this feed
            batch_size: Number of SKUs per request

        Returns:
            FetchStats with aggregated results
        """
        stats = FetchStats(start_time=datetime.utcnow())

        if not sku_ids:
            stats.end_time = datetime.utcnow()
            return stats

        # Process in batches
        for i in range(0, len(sku_ids), batch_size):
            batch = sku_ids[i : i + batch_size]

            batch_stats = await self.fetch_and_save_pricing(
                endpoint=endpoint,
                sku_ids=batch,
                vendor_id=vendor_id,
            )

            # Aggregate stats
            stats.total_requests += batch_stats.total_requests
            stats.successful += batch_stats.successful
            stats.failed += batch_stats.failed
            stats.records_fetched += batch_stats.records_fetched
            stats.records_saved += batch_stats.records_saved
            stats.rate_limited += batch_stats.rate_limited
            stats.errors.extend(batch_stats.errors)

        stats.end_time = datetime.utcnow()
        return stats

    async def health_check(self, endpoint: str = "/health") -> bool:
        """Check if the API is healthy and reachable.

        Args:
            endpoint: Health check endpoint

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = await self._make_request("GET", endpoint)
            return response.success
        except Exception as e:
            logger.error("API health check failed", error=str(e))
            return False


class VendorAPIRegistry:
    """Registry for managing multiple vendor API connectors."""

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """Initialize registry.

        Args:
            db_config: Database configuration
        """
        self.db_config = db_config
        self._connectors: dict[str, PricingAPIConnector] = {}

    def register(
        self,
        vendor_id: str,
        config: APIConnectorConfig,
    ) -> PricingAPIConnector:
        """Register a vendor API connector.

        Args:
            vendor_id: Vendor identifier
            config: API configuration

        Returns:
            The registered connector
        """
        connector = PricingAPIConnector(config, self.db_config)
        self._connectors[vendor_id] = connector
        logger.info("Registered API connector", vendor_id=vendor_id)
        return connector

    def get(self, vendor_id: str) -> Optional[PricingAPIConnector]:
        """Get a registered connector.

        Args:
            vendor_id: Vendor identifier

        Returns:
            Connector if found, None otherwise
        """
        return self._connectors.get(vendor_id)

    def list_vendors(self) -> list[str]:
        """List registered vendor IDs.

        Returns:
            List of vendor identifiers
        """
        return list(self._connectors.keys())

    async def fetch_all(
        self,
        sku_ids: Optional[list[str]] = None,
    ) -> dict[str, FetchStats]:
        """Fetch pricing from all registered vendors.

        Args:
            sku_ids: Optional list of SKU IDs to fetch

        Returns:
            Dictionary of fetch stats by vendor ID
        """
        results = {}

        for vendor_id, connector in self._connectors.items():
            try:
                stats = await connector.fetch_and_save_pricing(
                    vendor_id=vendor_id,
                    sku_ids=sku_ids,
                )
                results[vendor_id] = stats
            except Exception as e:
                logger.error(
                    "Error fetching from vendor",
                    vendor_id=vendor_id,
                    error=str(e),
                )
                results[vendor_id] = FetchStats(
                    errors=[str(e)],
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                )

        return results

    async def close_all(self):
        """Close all registered connectors."""
        for connector in self._connectors.values():
            await connector.close()


# Example vendor configurations for common API patterns
EXAMPLE_CONFIGS = {
    "rest_json_api_key": APIConnectorConfig(
        base_url="https://api.vendor.example.com/v1",
        auth_type=AuthType.API_KEY,
        api_key="YOUR_API_KEY",
        api_key_header="X-API-Key",
        response_mapping={
            "sku_id": "product_code",
            "price": ["pricing", "unit_price"],
            "currency": "currency_code",
            "geographic_region": "region",
        },
    ),
    "rest_json_bearer": APIConnectorConfig(
        base_url="https://api.supplier.example.com",
        auth_type=AuthType.BEARER_TOKEN,
        bearer_token="YOUR_BEARER_TOKEN",
        rate_limit_requests=1000,
        rate_limit_window=3600,
    ),
    "rest_json_basic": APIConnectorConfig(
        base_url="https://legacy.vendor.example.com/api",
        auth_type=AuthType.BASIC_AUTH,
        basic_auth=("username", "password"),
        timeout=60.0,
    ),
}
