"""Trend analysis visualization implementation."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go


class TrendAnalysisViz:
    """Trend analysis visualization.

    Creates historical and predictive trend charts.
    """

    def __init__(self) -> None:
        """Initialize the trend analysis visualization."""
        pass

    def create_price_trend_chart(
        self,
        historical_data: list[dict[str, Any]],
        forecast_data: list[dict[str, Any]] | None = None,
    ) -> go.Figure:
        """Create a price trend chart with optional forecast.

        Args:
            historical_data: List of historical price data points.
            forecast_data: Optional list of forecast data points.

        Returns:
            Plotly figure object.
        """
        fig = go.Figure()

        # Historical data
        hist_df = pd.DataFrame(historical_data)
        fig.add_trace(
            go.Scatter(
                x=hist_df["date"] if "date" in hist_df.columns else hist_df.index,
                y=hist_df["price"] if "price" in hist_df.columns else hist_df.iloc[:, 0],
                mode="lines+markers",
                name="Historical",
                line=dict(color="blue"),
            )
        )

        # Forecast data
        if forecast_data:
            forecast_df = pd.DataFrame(forecast_data)
            fig.add_trace(
                go.Scatter(
                    x=forecast_df["date"]
                    if "date" in forecast_df.columns
                    else forecast_df.index,
                    y=forecast_df["price"]
                    if "price" in forecast_df.columns
                    else forecast_df.iloc[:, 0],
                    mode="lines",
                    name="Forecast",
                    line=dict(color="red", dash="dash"),
                )
            )

            # Confidence interval
            if "lower" in forecast_df.columns and "upper" in forecast_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=forecast_df["date"],
                        y=forecast_df["upper"],
                        mode="lines",
                        line=dict(width=0),
                        showlegend=False,
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=forecast_df["date"],
                        y=forecast_df["lower"],
                        mode="lines",
                        line=dict(width=0),
                        fill="tonexty",
                        fillcolor="rgba(255, 0, 0, 0.2)",
                        name="Confidence Interval",
                    )
                )

        fig.update_layout(
            title="Price Trend Analysis",
            xaxis_title="Date",
            yaxis_title="Price ($/sqft)",
            hovermode="x unified",
        )

        return fig

    def create_volatility_chart(
        self,
        volatility_data: list[dict[str, Any]],
    ) -> go.Figure:
        """Create a price volatility chart.

        Args:
            volatility_data: List of volatility data points.

        Returns:
            Plotly figure object.
        """
        df = pd.DataFrame(volatility_data)

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df["date"] if "date" in df.columns else df.index,
                y=df["volatility"] if "volatility" in df.columns else df.iloc[:, 0],
                mode="lines",
                fill="tozeroy",
                name="Volatility",
                line=dict(color="orange"),
            )
        )

        fig.update_layout(
            title="Price Volatility Over Time",
            xaxis_title="Date",
            yaxis_title="Volatility (%)",
        )

        return fig

    def create_seasonality_chart(
        self,
        monthly_data: dict[str, float],
    ) -> go.Figure:
        """Create a seasonality pattern chart.

        Args:
            monthly_data: Dictionary of month -> average price.

        Returns:
            Plotly figure object.
        """
        months = list(monthly_data.keys())
        prices = list(monthly_data.values())
        avg_price = sum(prices) / len(prices) if prices else 0

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=months,
                y=prices,
                marker_color=[
                    "green" if p < avg_price else "red" for p in prices
                ],
                name="Monthly Average",
            )
        )

        fig.add_hline(
            y=avg_price,
            line_dash="dash",
            line_color="blue",
            annotation_text=f"Yearly Avg: ${avg_price:.2f}",
        )

        fig.update_layout(
            title="Seasonal Price Patterns",
            xaxis_title="Month",
            yaxis_title="Average Price ($/sqft)",
        )

        return fig
