"""Price normalization algorithm implementation."""

from pricepoint_intel.models.results import VendorResult


class PriceNormalizer:
    """Price normalization for geographic and volume adjustments.

    Normalizes prices across different regions and volume tiers
    to enable fair comparisons.
    """

    # Regional cost indices (relative to national average = 1.0)
    REGIONAL_COST_INDEX = {
        "northeast": 1.15,
        "southeast": 0.95,
        "midwest": 0.92,
        "southwest": 1.02,
        "west": 1.18,
        "pacific": 1.25,
    }

    # Zip code prefix to region mapping (simplified)
    ZIP_TO_REGION = {
        "0": "northeast",
        "1": "northeast",
        "2": "northeast",
        "3": "southeast",
        "4": "midwest",
        "5": "midwest",
        "6": "midwest",
        "7": "southwest",
        "8": "southwest",
        "9": "pacific",
    }

    # Volume discount tiers
    VOLUME_TIERS = [
        (0, 100, 1.0),      # 0-100 units: no discount
        (100, 500, 0.95),   # 100-500 units: 5% discount
        (500, 1000, 0.90),  # 500-1000 units: 10% discount
        (1000, 5000, 0.85), # 1000-5000 units: 15% discount
        (5000, float("inf"), 0.80),  # 5000+ units: 20% discount
    ]

    def __init__(self) -> None:
        """Initialize the price normalizer."""
        self._regional_index = self.REGIONAL_COST_INDEX.copy()
        self._volume_tiers = self.VOLUME_TIERS.copy()

    def get_region(self, location: str) -> str:
        """Determine the region from a location code.

        Args:
            location: Zip code or city name.

        Returns:
            Region name.
        """
        if location and location[0].isdigit():
            prefix = location[0]
            return self.ZIP_TO_REGION.get(prefix, "midwest")
        return "midwest"  # Default

    def get_regional_index(self, location: str) -> float:
        """Get the regional cost index for a location.

        Args:
            location: Zip code or city name.

        Returns:
            Regional cost index (1.0 = national average).
        """
        region = self.get_region(location)
        return self._regional_index.get(region, 1.0)

    def get_volume_multiplier(self, quantity: int) -> float:
        """Get the volume discount multiplier.

        Args:
            quantity: Number of units.

        Returns:
            Price multiplier (< 1.0 indicates discount).
        """
        for min_qty, max_qty, multiplier in self._volume_tiers:
            if min_qty <= quantity < max_qty:
                return multiplier
        return 1.0

    def normalize_price(
        self,
        price: float,
        from_location: str,
        to_location: str | None = None,
        quantity: int = 1,
    ) -> float:
        """Normalize a price for geographic and volume factors.

        Args:
            price: Original price.
            from_location: Source location of the price.
            to_location: Target location to normalize to (optional).
            quantity: Volume for discount calculation.

        Returns:
            Normalized price.
        """
        # Get regional indices
        from_index = self.get_regional_index(from_location)
        to_index = self.get_regional_index(to_location) if to_location else 1.0

        # Calculate regional adjustment
        regional_adjustment = to_index / from_index if from_index != 0 else 1.0

        # Get volume multiplier
        volume_multiplier = self.get_volume_multiplier(quantity)

        # Apply adjustments
        normalized_price = price * regional_adjustment * volume_multiplier

        return round(normalized_price, 2)

    def normalize_prices(
        self,
        vendors: list[VendorResult],
        target_location: str,
    ) -> list[VendorResult]:
        """Normalize prices for a list of vendor results.

        Args:
            vendors: List of vendor results with prices.
            target_location: Target location to normalize to.

        Returns:
            List of vendor results with normalized prices.
        """
        normalized = []
        # Calculate target index for future use in production
        _target_index = self.get_regional_index(target_location)

        for vendor in vendors:
            # For now, assume vendor prices are already at their local rate
            # In production, we would know each vendor's location
            normalized_price = vendor.price_per_unit

            # Create new vendor result with normalized price
            normalized.append(
                VendorResult(
                    vendor_id=vendor.vendor_id,
                    vendor_name=vendor.vendor_name,
                    price_per_unit=normalized_price,
                    unit=vendor.unit,
                    distance_miles=vendor.distance_miles,
                    last_updated=vendor.last_updated,
                    confidence_score=vendor.confidence_score,
                )
            )

        return normalized

    def calculate_geographic_premium(self, location: str) -> float:
        """Calculate the geographic premium/discount for a location.

        Args:
            location: Zip code or city name.

        Returns:
            Premium as a percentage (e.g., 0.15 = 15% premium).
        """
        index = self.get_regional_index(location)
        return index - 1.0
