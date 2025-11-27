"""Geographic pricing visualization implementation."""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class GeographicPricingViz:
    """Geographic pricing visualization.

    Creates interactive cost maps showing regional pricing variations.
    """

    def __init__(self) -> None:
        """Initialize the geographic pricing visualization."""
        pass

    def create_price_heatmap(
        self,
        pricing_data: list[dict[str, Any]],
        center_location: tuple[float, float] | None = None,
    ) -> go.Figure:
        """Create a price heatmap visualization.

        Args:
            pricing_data: List of pricing data with location info.
            center_location: Optional center point (lat, lon).

        Returns:
            Plotly figure object.
        """
        # Convert to DataFrame
        df = pd.DataFrame(pricing_data)

        # Create scatter map
        fig = px.scatter_mapbox(
            df,
            lat="latitude" if "latitude" in df.columns else None,
            lon="longitude" if "longitude" in df.columns else None,
            color="price",
            size="vendor_count" if "vendor_count" in df.columns else None,
            hover_name="location" if "location" in df.columns else None,
            color_continuous_scale="RdYlGn_r",
            mapbox_style="carto-positron",
            title="Geographic Price Distribution",
        )

        if center_location:
            fig.update_layout(
                mapbox=dict(
                    center=dict(lat=center_location[0], lon=center_location[1]),
                    zoom=8,
                )
            )

        return fig

    def create_regional_comparison(
        self,
        regional_data: dict[str, float],
    ) -> go.Figure:
        """Create a regional price comparison chart.

        Args:
            regional_data: Dictionary of region -> average price.

        Returns:
            Plotly figure object.
        """
        regions = list(regional_data.keys())
        prices = list(regional_data.values())
        national_avg = sum(prices) / len(prices) if prices else 0

        fig = go.Figure()

        # Add bar chart
        fig.add_trace(
            go.Bar(
                x=regions,
                y=prices,
                marker_color=[
                    "green" if p < national_avg else "red" for p in prices
                ],
                name="Regional Price",
            )
        )

        # Add national average line
        fig.add_hline(
            y=national_avg,
            line_dash="dash",
            line_color="blue",
            annotation_text=f"National Avg: ${national_avg:.2f}",
        )

        fig.update_layout(
            title="Regional Price Comparison",
            xaxis_title="Region",
            yaxis_title="Average Price ($/sqft)",
        )

        return fig

    def create_distance_price_scatter(
        self,
        vendor_data: list[dict[str, Any]],
    ) -> go.Figure:
        """Create a scatter plot of distance vs price.

        Args:
            vendor_data: List of vendor data with distance and price.

        Returns:
            Plotly figure object.
        """
        df = pd.DataFrame(vendor_data)

        fig = px.scatter(
            df,
            x="distance_miles" if "distance_miles" in df.columns else "distance",
            y="price_per_unit" if "price_per_unit" in df.columns else "price",
            hover_name="vendor_name" if "vendor_name" in df.columns else None,
            title="Price vs Distance from Location",
            labels={
                "distance_miles": "Distance (miles)",
                "price_per_unit": "Price ($/sqft)",
            },
        )

        return fig
