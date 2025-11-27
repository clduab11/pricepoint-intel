"""Export engine implementation."""

import csv
import io
import json
from datetime import datetime
from typing import Any

from pricepoint_intel.models.results import QueryResults


class ExportEngine:
    """Export engine for reports and data feeds.

    Exports query results in various formats.
    """

    def __init__(self) -> None:
        """Initialize the export engine."""
        pass

    def export_json(
        self,
        results: QueryResults,
        pretty: bool = True,
    ) -> str:
        """Export results as JSON.

        Args:
            results: Query results to export.
            pretty: Whether to format with indentation.

        Returns:
            JSON string.
        """
        data = results.to_dict()
        data["exported_at"] = datetime.now().isoformat()

        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)

    def export_csv(
        self,
        results: QueryResults,
        include_vendors: bool = True,
        include_procurement: bool = True,
    ) -> str:
        """Export results as CSV.

        Args:
            results: Query results to export.
            include_vendors: Include vendor data.
            include_procurement: Include procurement records.

        Returns:
            CSV string.
        """
        output = io.StringIO()

        # Write summary
        output.write("# Query Summary\n")
        output.write(f"Product,{results.product}\n")
        output.write(f"Location,{results.location}\n")
        output.write(f"Radius (miles),{results.radius_miles}\n")
        output.write(f"Vendor Count,{results.vendor_count}\n")
        if results.price_range:
            output.write(f"Price Range,${results.price_range[0]:.2f}-${results.price_range[1]:.2f}\n")
        if results.market_average:
            output.write(f"Market Average,${results.market_average:.2f}\n")
        output.write("\n")

        # Write vendor data
        if include_vendors and results.vendors:
            output.write("# Vendors\n")
            writer = csv.writer(output)
            writer.writerow([
                "Vendor ID",
                "Vendor Name",
                "Price per Unit",
                "Unit",
                "Distance (miles)",
                "Last Updated",
                "Confidence Score",
            ])
            for vendor in results.vendors:
                writer.writerow([
                    vendor.vendor_id,
                    vendor.vendor_name,
                    vendor.price_per_unit,
                    vendor.unit,
                    vendor.distance_miles,
                    vendor.last_updated,
                    vendor.confidence_score,
                ])
            output.write("\n")

        # Write procurement records
        if include_procurement and results.procurement_records:
            output.write("# Procurement Records\n")
            writer = csv.writer(output)
            writer.writerow([
                "Record ID",
                "Source",
                "Entity Name",
                "Contract Value",
                "Unit Price",
                "Date",
                "Location",
            ])
            for record in results.procurement_records:
                writer.writerow([
                    record.record_id,
                    record.source,
                    record.entity_name,
                    record.contract_value,
                    record.unit_price,
                    record.date,
                    record.location,
                ])

        return output.getvalue()

    def export_excel_data(
        self,
        results: QueryResults,
    ) -> dict[str, list[dict[str, Any]]]:
        """Export results as Excel-compatible data.

        Args:
            results: Query results to export.

        Returns:
            Dictionary of sheet names to row data.
        """
        return {
            "Summary": [
                {
                    "Metric": "Product",
                    "Value": results.product,
                },
                {
                    "Metric": "Location",
                    "Value": results.location,
                },
                {
                    "Metric": "Radius (miles)",
                    "Value": results.radius_miles,
                },
                {
                    "Metric": "Vendor Count",
                    "Value": results.vendor_count,
                },
                {
                    "Metric": "Price Range",
                    "Value": f"${results.price_range[0]:.2f}-${results.price_range[1]:.2f}"
                    if results.price_range
                    else "N/A",
                },
                {
                    "Metric": "Market Average",
                    "Value": f"${results.market_average:.2f}"
                    if results.market_average
                    else "N/A",
                },
            ],
            "Vendors": [v.to_dict() for v in results.vendors],
            "Procurement": [r.to_dict() for r in results.procurement_records],
            "Relationships": [s.to_dict() for s in results.supplier_relationships],
        }

    def generate_report_html(
        self,
        results: QueryResults,
        title: str = "PricePoint Intel Report",
    ) -> str:
        """Generate an HTML report.

        Args:
            results: Query results to export.
            title: Report title.

        Returns:
            HTML string.
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #ddd; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="summary">
        <h2>Query Summary</h2>
        <p><strong>Product:</strong> {results.product}</p>
        <p><strong>Location:</strong> {results.location}</p>
        <p><strong>Search Radius:</strong> {results.radius_miles} miles</p>
        <p><strong>Vendors Found:</strong> {results.vendor_count}</p>
"""

        if results.price_range:
            html += f"        <p><strong>Price Range:</strong> ${results.price_range[0]:.2f} - ${results.price_range[1]:.2f}</p>\n"

        if results.market_average:
            html += f"        <p><strong>Market Average:</strong> ${results.market_average:.2f}</p>\n"

        html += """    </div>

    <h2>Vendor Pricing</h2>
    <table>
        <tr>
            <th>Vendor</th>
            <th>Price</th>
            <th>Distance</th>
            <th>Last Updated</th>
        </tr>
"""

        for vendor in results.vendors[:20]:  # Limit to top 20
            html += f"""        <tr>
            <td>{vendor.vendor_name}</td>
            <td>${vendor.price_per_unit:.2f}/{vendor.unit}</td>
            <td>{vendor.distance_miles:.1f} miles</td>
            <td>{vendor.last_updated}</td>
        </tr>
"""

        html += """    </table>
</body>
</html>"""

        return html
