"""Tests for the core IntelligenceEngine."""

from pricepoint_intel import IntelligenceEngine
from pricepoint_intel.models.results import QueryResults


class TestIntelligenceEngine:
    """Test suite for IntelligenceEngine class."""

    def test_engine_initialization(self):
        """Test that the engine initializes correctly."""
        engine = IntelligenceEngine()
        assert engine is not None

    def test_query_returns_results(self):
        """Test that query returns QueryResults object."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
            radius_miles=50,
        )

        assert isinstance(results, QueryResults)
        assert results.product == "laminate flooring"
        assert results.location == "35242"
        assert results.radius_miles == 50

    def test_query_returns_vendors(self):
        """Test that query returns vendor data."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
        )

        assert results.vendor_count > 0
        assert len(results.vendors) > 0

    def test_query_price_range(self):
        """Test that price range is calculated correctly."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
        )

        assert results.price_range is not None
        min_price, max_price = results.price_range
        assert min_price <= max_price
        assert min_price > 0

    def test_query_market_average(self):
        """Test that market average is calculated."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
        )

        assert results.market_average is not None
        assert results.market_average > 0

    def test_query_procurement_records(self):
        """Test that procurement records are returned."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
            include_procurement=True,
        )

        assert len(results.procurement_records) > 0

    def test_query_supplier_relationships(self):
        """Test that supplier relationships are returned."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
            include_relationships=True,
        )

        assert len(results.supplier_relationships) > 0

    def test_query_benchmarks(self):
        """Test that benchmarks are calculated."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
            include_benchmarks=True,
        )

        assert results.benchmark is not None
        assert results.benchmark.industry_average > 0

    def test_query_risk_scores(self):
        """Test that risk scores are calculated."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
            include_risk_scores=True,
        )

        assert results.risk_score is not None
        assert 0 <= results.risk_score.overall_score <= 1

    def test_query_time_tracking(self):
        """Test that query time is tracked."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
        )

        assert results.query_time_ms > 0

    def test_results_summary(self):
        """Test that results summary is generated."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
        )

        summary = results.summary()
        assert isinstance(summary, str)
        assert "laminate flooring" in summary
        assert "vendors found" in summary

    def test_results_to_dict(self):
        """Test that results can be converted to dictionary."""
        engine = IntelligenceEngine()
        results = engine.query(
            product="laminate flooring",
            location="35242",
        )

        data = results.to_dict()
        assert isinstance(data, dict)
        assert "product" in data
        assert "vendors" in data
        assert "price_range" in data


class TestQueryResults:
    """Test suite for QueryResults class."""

    def test_empty_results(self):
        """Test empty results object."""
        results = QueryResults(
            product="test",
            location="00000",
            radius_miles=10,
        )

        assert results.vendor_count == 0
        assert results.price_range is None
        assert results.market_average is None

    def test_results_properties(self):
        """Test results property calculations."""
        from pricepoint_intel.models.results import VendorResult

        results = QueryResults(
            product="test",
            location="00000",
            radius_miles=10,
            vendors=[
                VendorResult(
                    vendor_id="V001",
                    vendor_name="Vendor 1",
                    price_per_unit=2.00,
                    unit="sqft",
                    distance_miles=5.0,
                    last_updated="2024-01-15",
                ),
                VendorResult(
                    vendor_id="V002",
                    vendor_name="Vendor 2",
                    price_per_unit=4.00,
                    unit="sqft",
                    distance_miles=10.0,
                    last_updated="2024-01-15",
                ),
            ],
        )

        assert results.vendor_count == 2
        assert results.price_range == (2.00, 4.00)
        assert results.market_average == 3.00
