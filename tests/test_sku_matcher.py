"""Tests for the SKU Matcher module."""

import pytest

from pricepoint_intel.intelligence_engine.sku_matcher import SKUMatcher


class TestSKUMatcher:
    """Test suite for SKUMatcher class."""

    def test_matcher_initialization(self):
        """Test that matcher initializes correctly."""
        matcher = SKUMatcher()
        assert matcher is not None
        assert matcher.get_catalog_size() > 0

    def test_match_exact_product(self):
        """Test matching with exact product name."""
        matcher = SKUMatcher()
        results = matcher.match("laminate flooring")

        assert len(results) > 0
        # Check that results are sorted by score
        scores = [r.match_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_match_partial_product(self):
        """Test matching with partial product name."""
        matcher = SKUMatcher()
        results = matcher.match("laminate")

        assert len(results) > 0

    def test_match_with_category_filter(self):
        """Test matching with category filter."""
        matcher = SKUMatcher()
        results = matcher.match("flooring", category="flooring")

        assert len(results) > 0
        for result in results:
            assert result.category == "flooring"

    def test_match_with_max_results(self):
        """Test matching with max results limit."""
        matcher = SKUMatcher()
        results = matcher.match("flooring", max_results=3)

        assert len(results) <= 3

    def test_match_returns_sku_match(self):
        """Test that match returns SKUMatch objects."""
        matcher = SKUMatcher()
        results = matcher.match("laminate flooring")

        if results:
            result = results[0]
            assert hasattr(result, "sku_id")
            assert hasattr(result, "product_name")
            assert hasattr(result, "match_score")
            assert hasattr(result, "source")
            assert hasattr(result, "category")

    def test_match_score_range(self):
        """Test that match scores are in valid range."""
        matcher = SKUMatcher()
        results = matcher.match("laminate flooring")

        for result in results:
            assert 0 <= result.match_score <= 1

    def test_no_matches_below_threshold(self):
        """Test that no results are below min match score."""
        matcher = SKUMatcher(min_match_score=0.80)
        results = matcher.match("xyz123")  # Unlikely to match

        # All results should be above threshold
        for result in results:
            assert result.match_score >= 0.80

    def test_add_to_catalog(self):
        """Test adding products to catalog."""
        matcher = SKUMatcher()
        initial_size = matcher.get_catalog_size()

        matcher.add_to_catalog({
            "sku_id": "TEST-001",
            "product_name": "Test Product",
            "category": "test",
        })

        assert matcher.get_catalog_size() == initial_size + 1

    def test_add_to_catalog_validation(self):
        """Test that add_to_catalog validates required fields."""
        matcher = SKUMatcher()

        with pytest.raises(ValueError):
            matcher.add_to_catalog({
                "sku_id": "TEST-001",
                # Missing product_name and category
            })

    def test_match_to_dict(self):
        """Test SKUMatch to_dict method."""
        matcher = SKUMatcher()
        results = matcher.match("laminate flooring")

        if results:
            data = results[0].to_dict()
            assert isinstance(data, dict)
            assert "sku_id" in data
            assert "product_name" in data
            assert "match_score" in data
