"""Dash application for PricePoint Intel research dashboard."""

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

from pricepoint_intel import IntelligenceEngine


def create_dash_app() -> dash.Dash:
    """Create and configure the Dash application.

    Returns:
        Configured Dash application.
    """
    # Initialize the intelligence engine
    engine = IntelligenceEngine()

    # Create Dash app
    app = dash.Dash(
        __name__,
        title="PricePoint Intel",
        update_title="Loading...",
        suppress_callback_exceptions=True,
    )

    # Define layout
    app.layout = html.Div([
        # Header
        html.Div([
            html.H1("PricePoint Intel", className="header-title"),
            html.P(
                "SKU-Level Competitive Intelligence Platform",
                className="header-subtitle"
            ),
        ], className="header"),

        # Main content
        html.Div([
            # Search panel
            html.Div([
                html.H3("Intelligence Query"),
                html.Label("Product:"),
                dcc.Input(
                    id="product-input",
                    type="text",
                    placeholder="e.g., laminate flooring",
                    value="laminate flooring",
                    className="input-field",
                ),
                html.Label("Location (ZIP):"),
                dcc.Input(
                    id="location-input",
                    type="text",
                    placeholder="e.g., 35242",
                    value="35242",
                    className="input-field",
                ),
                html.Label("Search Radius (miles):"),
                dcc.Slider(
                    id="radius-slider",
                    min=10,
                    max=200,
                    step=10,
                    value=50,
                    marks={i: str(i) for i in range(0, 201, 50)},
                ),
                html.Button(
                    "Search",
                    id="search-button",
                    className="search-button",
                ),
            ], className="search-panel"),

            # Results panel
            html.Div([
                # Summary cards
                html.Div([
                    html.Div([
                        html.H4("Vendors Found"),
                        html.P(id="vendor-count", className="metric-value"),
                    ], className="metric-card"),
                    html.Div([
                        html.H4("Price Range"),
                        html.P(id="price-range", className="metric-value"),
                    ], className="metric-card"),
                    html.Div([
                        html.H4("Market Average"),
                        html.P(id="market-average", className="metric-value"),
                    ], className="metric-card"),
                    html.Div([
                        html.H4("Procurement Records"),
                        html.P(id="procurement-count", className="metric-value"),
                    ], className="metric-card"),
                ], className="metrics-row"),

                # Charts
                html.Div([
                    html.Div([
                        dcc.Graph(id="price-distribution-chart"),
                    ], className="chart-container"),
                    html.Div([
                        dcc.Graph(id="vendor-comparison-chart"),
                    ], className="chart-container"),
                ], className="charts-row"),

                # Vendor table
                html.Div([
                    html.H3("Top Vendors"),
                    html.Div(id="vendor-table"),
                ], className="table-container"),

            ], className="results-panel"),

        ], className="main-content"),

        # Footer
        html.Div([
            html.P("© 2024 Parallax Analytics, LLC. Research Phase."),
        ], className="footer"),

        # Store for results data
        dcc.Store(id="results-store"),

    ], className="app-container")

    # Add CSS styles
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                * { box-sizing: border-box; margin: 0; padding: 0; }
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
                .app-container { min-height: 100vh; display: flex; flex-direction: column; }
                .header { background: linear-gradient(135deg, #1a237e 0%, #4a148c 100%); color: white; padding: 20px 40px; }
                .header-title { font-size: 2em; margin-bottom: 5px; }
                .header-subtitle { opacity: 0.8; }
                .main-content { display: flex; flex: 1; padding: 20px; gap: 20px; }
                .search-panel { width: 300px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .search-panel h3 { margin-bottom: 15px; color: #333; }
                .search-panel label { display: block; margin-top: 15px; margin-bottom: 5px; color: #666; font-weight: 500; }
                .input-field { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
                .search-button { width: 100%; margin-top: 20px; padding: 12px; background: #1a237e; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }
                .search-button:hover { background: #303f9f; }
                .results-panel { flex: 1; }
                .metrics-row { display: flex; gap: 15px; margin-bottom: 20px; }
                .metric-card { flex: 1; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
                .metric-card h4 { color: #666; font-size: 14px; margin-bottom: 10px; }
                .metric-value { font-size: 24px; font-weight: bold; color: #1a237e; }
                .charts-row { display: flex; gap: 15px; margin-bottom: 20px; }
                .chart-container { flex: 1; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .table-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .table-container h3 { margin-bottom: 15px; color: #333; }
                .vendor-table { width: 100%; border-collapse: collapse; }
                .vendor-table th, .vendor-table td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
                .vendor-table th { background: #f9f9f9; color: #666; font-weight: 600; }
                .vendor-table tr:hover { background: #f5f5f5; }
                .footer { background: #333; color: white; padding: 15px 40px; text-align: center; }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''

    # Define callbacks
    @app.callback(
        [
            Output("results-store", "data"),
            Output("vendor-count", "children"),
            Output("price-range", "children"),
            Output("market-average", "children"),
            Output("procurement-count", "children"),
        ],
        Input("search-button", "n_clicks"),
        [
            State("product-input", "value"),
            State("location-input", "value"),
            State("radius-slider", "value"),
        ],
        prevent_initial_call=False,
    )
    def execute_search(n_clicks, product, location, radius):
        """Execute search and update metrics."""
        # Run query
        results = engine.query(
            product=product or "laminate flooring",
            location=location or "35242",
            radius_miles=radius or 50,
        )

        # Format metrics
        vendor_count = str(results.vendor_count)
        price_range = (
            f"${results.price_range[0]:.2f} - ${results.price_range[1]:.2f}"
            if results.price_range else "N/A"
        )
        market_avg = f"${results.market_average:.2f}" if results.market_average else "N/A"
        procurement_count = str(len(results.procurement_records))

        return (
            results.to_dict(),
            vendor_count,
            price_range,
            market_avg,
            procurement_count,
        )

    @app.callback(
        Output("price-distribution-chart", "figure"),
        Input("results-store", "data"),
    )
    def update_price_distribution(data):
        """Update price distribution chart."""
        if not data or not data.get("vendors"):
            return go.Figure()

        prices = [v["price_per_unit"] for v in data["vendors"]]

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=prices,
            nbinsx=15,
            marker_color="#1a237e",
        ))

        if data.get("market_average"):
            fig.add_vline(
                x=data["market_average"],
                line_dash="dash",
                line_color="red",
                annotation_text=f"Avg: ${data['market_average']:.2f}",
            )

        fig.update_layout(
            title="Price Distribution",
            xaxis_title="Price ($/sqft)",
            yaxis_title="Count",
            margin=dict(l=40, r=20, t=40, b=40),
        )

        return fig

    @app.callback(
        Output("vendor-comparison-chart", "figure"),
        Input("results-store", "data"),
    )
    def update_vendor_comparison(data):
        """Update vendor comparison chart."""
        if not data or not data.get("vendors"):
            return go.Figure()

        # Get top 10 vendors by price
        vendors = sorted(data["vendors"], key=lambda x: x["price_per_unit"])[:10]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[v["vendor_name"] for v in vendors],
            y=[v["price_per_unit"] for v in vendors],
            marker_color="#4a148c",
        ))

        fig.update_layout(
            title="Top 10 Vendors by Price",
            xaxis_title="Vendor",
            yaxis_title="Price ($/sqft)",
            xaxis_tickangle=-45,
            margin=dict(l=40, r=20, t=40, b=100),
        )

        return fig

    @app.callback(
        Output("vendor-table", "children"),
        Input("results-store", "data"),
    )
    def update_vendor_table(data):
        """Update vendor table."""
        if not data or not data.get("vendors"):
            return html.P("No vendors found.")

        vendors = data["vendors"][:20]  # Show top 20

        return html.Table([
            html.Thead([
                html.Tr([
                    html.Th("Vendor"),
                    html.Th("Price"),
                    html.Th("Distance"),
                    html.Th("Last Updated"),
                    html.Th("Confidence"),
                ])
            ]),
            html.Tbody([
                html.Tr([
                    html.Td(v["vendor_name"]),
                    html.Td(f"${v['price_per_unit']:.2f}/{v['unit']}"),
                    html.Td(f"{v['distance_miles']:.1f} mi"),
                    html.Td(v["last_updated"]),
                    html.Td(f"{v['confidence_score']:.0%}"),
                ]) for v in vendors
            ])
        ], className="vendor-table")

    return app


if __name__ == "__main__":
    app = create_dash_app()
    app.run_server(debug=True, port=8050)
