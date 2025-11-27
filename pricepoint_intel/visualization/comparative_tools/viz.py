"""Comparative tools visualization implementation."""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class ComparativeToolsViz:
    """Comparative analysis visualization tools.

    Creates multi-vendor benchmarking and comparison charts.
    """

    def __init__(self) -> None:
        """Initialize the comparative tools visualization."""
        pass

    def create_vendor_comparison(
        self,
        vendor_data: list[dict[str, Any]],
    ) -> go.Figure:
        """Create a vendor comparison bar chart.

        Args:
            vendor_data: List of vendor pricing data.

        Returns:
            Plotly figure object.
        """
        df = pd.DataFrame(vendor_data)

        fig = px.bar(
            df,
            x="vendor_name" if "vendor_name" in df.columns else df.columns[0],
            y="price_per_unit" if "price_per_unit" in df.columns else df.columns[1],
            color="vendor_name" if "vendor_name" in df.columns else None,
            title="Vendor Price Comparison",
            labels={
                "vendor_name": "Vendor",
                "price_per_unit": "Price ($/sqft)",
            },
        )

        fig.update_layout(showlegend=False)

        return fig

    def create_benchmark_gauge(
        self,
        current_price: float,
        benchmark: dict[str, float],
    ) -> go.Figure:
        """Create a benchmark gauge chart.

        Args:
            current_price: Current purchase price.
            benchmark: Benchmark data with percentiles.

        Returns:
            Plotly figure object.
        """
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=current_price,
                delta={"reference": benchmark.get("industry_average", current_price)},
                gauge={
                    "axis": {
                        "range": [
                            benchmark.get("percentile_25", current_price * 0.8),
                            benchmark.get("percentile_75", current_price * 1.2),
                        ]
                    },
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {
                            "range": [
                                benchmark.get("percentile_25", 0),
                                benchmark.get("percentile_50", 0),
                            ],
                            "color": "lightgreen",
                        },
                        {
                            "range": [
                                benchmark.get("percentile_50", 0),
                                benchmark.get("percentile_75", 0),
                            ],
                            "color": "lightyellow",
                        },
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": benchmark.get("industry_average", current_price),
                    },
                },
                title={"text": "Price vs Industry Benchmark"},
            )
        )

        return fig

    def create_multi_metric_radar(
        self,
        vendor_metrics: list[dict[str, Any]],
    ) -> go.Figure:
        """Create a radar chart for multi-metric vendor comparison.

        Args:
            vendor_metrics: List of vendor metric dictionaries.

        Returns:
            Plotly figure object.
        """
        fig = go.Figure()

        for vendor in vendor_metrics:
            categories = list(vendor.get("metrics", {}).keys())
            values = list(vendor.get("metrics", {}).values())
            values.append(values[0])  # Close the polygon
            categories.append(categories[0])

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill="toself",
                    name=vendor.get("vendor_name", "Unknown"),
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            title="Multi-Metric Vendor Comparison",
        )

        return fig

    def create_price_distribution(
        self,
        prices: list[float],
        current_price: float | None = None,
    ) -> go.Figure:
        """Create a price distribution histogram.

        Args:
            prices: List of prices.
            current_price: Optional current price to highlight.

        Returns:
            Plotly figure object.
        """
        fig = go.Figure()

        fig.add_trace(
            go.Histogram(
                x=prices,
                nbinsx=20,
                name="Price Distribution",
                marker_color="lightblue",
            )
        )

        if current_price is not None:
            fig.add_vline(
                x=current_price,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Current: ${current_price:.2f}",
            )

        fig.update_layout(
            title="Price Distribution",
            xaxis_title="Price ($/sqft)",
            yaxis_title="Count",
        )

        return fig
