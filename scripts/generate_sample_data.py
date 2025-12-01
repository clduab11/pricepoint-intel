#!/usr/bin/env python3
"""Generate sample dataset for PricePoint Intel.

Creates 50-100 SKUs across multiple categories, 5 vendors, and 3 geographic regions.
Outputs CSV files that can be imported using the data ingestion pipeline.
"""

import csv
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Seed for reproducibility
random.seed(42)

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "sample"

# ============================================
# Product Categories and Names
# ============================================

PRODUCT_DATA = {
    "flooring": [
        ("Oak Hardwood Plank", 8.50, 12.00),
        ("Maple Hardwood Strip", 7.00, 10.50),
        ("Bamboo Engineered", 6.00, 9.00),
        ("Luxury Vinyl Plank", 3.50, 6.00),
        ("Porcelain Tile 12x12", 2.50, 5.00),
        ("Ceramic Tile 18x18", 2.00, 4.50),
        ("Laminate Flooring", 1.50, 3.50),
        ("Cork Flooring Tile", 5.00, 8.00),
        ("Rubber Flooring Roll", 4.00, 7.00),
        ("Carpet Tile Commercial", 3.00, 6.50),
    ],
    "building_materials": [
        ("Drywall Sheet 4x8", 10.00, 15.00),
        ("Plywood 3/4 CDX", 45.00, 65.00),
        ("OSB Sheathing 7/16", 25.00, 38.00),
        ("Concrete Mix 80lb", 5.00, 8.00),
        ("Mortar Mix 60lb", 6.00, 10.00),
        ("Rebar #4 20ft", 8.00, 12.00),
        ("Fiberglass Insulation R-13", 0.50, 1.00),
        ("Foam Board Insulation 2in", 15.00, 22.00),
        ("House Wrap Roll", 120.00, 180.00),
        ("Roofing Shingles Bundle", 30.00, 45.00),
    ],
    "electrical": [
        ("Romex Wire 12/2 250ft", 85.00, 125.00),
        ("Electrical Panel 200A", 180.00, 280.00),
        ("Circuit Breaker 20A", 8.00, 15.00),
        ("LED Recessed Light 6in", 12.00, 22.00),
        ("Outlet Receptacle 15A", 1.50, 3.50),
        ("Light Switch Single Pole", 1.00, 3.00),
        ("Conduit EMT 10ft", 4.00, 8.00),
        ("Wire Connector Pack", 5.00, 10.00),
        ("Junction Box Metal", 2.00, 5.00),
        ("Ceiling Fan 52in", 80.00, 150.00),
    ],
    "plumbing": [
        ("PVC Pipe 3in 10ft", 8.00, 14.00),
        ("Copper Pipe 1/2in 10ft", 25.00, 40.00),
        ("PEX Tubing 1/2in 100ft", 35.00, 55.00),
        ("Toilet Standard", 120.00, 200.00),
        ("Bathroom Sink Pedestal", 80.00, 150.00),
        ("Kitchen Faucet Chrome", 60.00, 120.00),
        ("Water Heater 50gal", 450.00, 700.00),
        ("Shower Valve Trim", 40.00, 80.00),
        ("Garbage Disposal 3/4HP", 100.00, 180.00),
        ("Supply Line Braided", 8.00, 15.00),
    ],
    "hvac": [
        ("Furnace Filter 20x25x1", 8.00, 18.00),
        ("Ductwork Flexible 6in", 15.00, 25.00),
        ("Thermostat Programmable", 35.00, 80.00),
        ("AC Condenser Unit", 1200.00, 2200.00),
        ("Ventilation Fan 80CFM", 50.00, 100.00),
        ("Duct Tape HVAC", 8.00, 15.00),
        ("Register Vent 4x10", 5.00, 12.00),
        ("Mini Split Unit 12000BTU", 800.00, 1400.00),
        ("Refrigerant R410A", 80.00, 140.00),
        ("Duct Insulation Wrap", 20.00, 35.00),
    ],
    "hardware": [
        ("Door Knob Entry", 25.00, 50.00),
        ("Deadbolt Lock", 30.00, 70.00),
        ("Cabinet Hinge Pair", 4.00, 10.00),
        ("Drawer Slide 18in", 12.00, 25.00),
        ("Shelf Bracket Heavy", 6.00, 15.00),
        ("Anchor Bolt Set", 8.00, 16.00),
        ("Wood Screw Box 100ct", 10.00, 20.00),
        ("Concrete Anchor Pack", 12.00, 22.00),
        ("Door Closer Commercial", 40.00, 80.00),
        ("Weather Stripping Kit", 15.00, 30.00),
    ],
    "lumber": [
        ("2x4 Stud 8ft", 4.00, 8.00),
        ("2x6 SPF 12ft", 8.00, 14.00),
        ("4x4 Post Treated", 12.00, 20.00),
        ("Deck Board 5/4x6 16ft", 18.00, 30.00),
        ("Furring Strip 1x2", 2.00, 4.00),
        ("Cedar Board 1x6", 6.00, 12.00),
        ("Trim Board Primed 1x4", 3.00, 6.00),
        ("LVL Beam 1-3/4x9-1/2", 45.00, 75.00),
        ("Fence Picket 1x6", 3.00, 6.00),
        ("Plywood Baltic Birch", 55.00, 85.00),
    ],
    "paint": [
        ("Interior Paint Gallon", 30.00, 55.00),
        ("Exterior Paint Gallon", 35.00, 65.00),
        ("Primer Gallon", 20.00, 40.00),
        ("Stain Penetrating Qt", 15.00, 30.00),
        ("Paint Brush 3in Pro", 10.00, 22.00),
        ("Roller Cover 9in", 6.00, 14.00),
        ("Painter Tape 2in", 5.00, 12.00),
        ("Drop Cloth 9x12", 8.00, 18.00),
        ("Caulk Tube Silicone", 6.00, 12.00),
        ("Spray Paint Can", 5.00, 10.00),
    ],
    "tools": [
        ("Cordless Drill 20V", 100.00, 180.00),
        ("Circular Saw 7-1/4in", 120.00, 200.00),
        ("Hammer 16oz Fiberglass", 20.00, 40.00),
        ("Tape Measure 25ft", 12.00, 25.00),
        ("Level 48in", 30.00, 60.00),
        ("Screwdriver Set 10pc", 15.00, 35.00),
        ("Pliers Set 3pc", 20.00, 45.00),
        ("Socket Set 40pc", 40.00, 90.00),
        ("Safety Glasses", 5.00, 15.00),
        ("Work Gloves Pair", 8.00, 20.00),
    ],
}

# ============================================
# Vendors
# ============================================

VENDORS = [
    {
        "vendor_id": "VENDOR-001",
        "vendor_name": "BuildMart Supply",
        "vendor_type": "distributor",
        "contact_email": "sales@buildmart.example.com",
        "contact_phone": "555-100-1000",
        "website": "https://buildmart.example.com",
        "headquarters_city": "Atlanta",
        "headquarters_state": "GA",
        "headquarters_country": "USA",
        "headquarters_zip": "30301",
        "latitude": 33.749,
        "longitude": -84.388,
        "reliability_score": 0.92,
        "avg_lead_time_days": 3,
        "min_order_value": 100.00,
    },
    {
        "vendor_id": "VENDOR-002",
        "vendor_name": "Wholesale Materials Corp",
        "vendor_type": "wholesaler",
        "contact_email": "orders@wholesalematerials.example.com",
        "contact_phone": "555-200-2000",
        "website": "https://wholesalematerials.example.com",
        "headquarters_city": "Chicago",
        "headquarters_state": "IL",
        "headquarters_country": "USA",
        "headquarters_zip": "60601",
        "latitude": 41.878,
        "longitude": -87.630,
        "reliability_score": 0.88,
        "avg_lead_time_days": 5,
        "min_order_value": 250.00,
    },
    {
        "vendor_id": "VENDOR-003",
        "vendor_name": "Pacific Building Products",
        "vendor_type": "distributor",
        "contact_email": "info@pacificbp.example.com",
        "contact_phone": "555-300-3000",
        "website": "https://pacificbp.example.com",
        "headquarters_city": "Los Angeles",
        "headquarters_state": "CA",
        "headquarters_country": "USA",
        "headquarters_zip": "90001",
        "latitude": 34.052,
        "longitude": -118.244,
        "reliability_score": 0.95,
        "avg_lead_time_days": 4,
        "min_order_value": 150.00,
    },
    {
        "vendor_id": "VENDOR-004",
        "vendor_name": "Northeast Hardware Direct",
        "vendor_type": "distributor",
        "contact_email": "support@nehardware.example.com",
        "contact_phone": "555-400-4000",
        "website": "https://nehardware.example.com",
        "headquarters_city": "Boston",
        "headquarters_state": "MA",
        "headquarters_country": "USA",
        "headquarters_zip": "02101",
        "latitude": 42.361,
        "longitude": -71.057,
        "reliability_score": 0.90,
        "avg_lead_time_days": 2,
        "min_order_value": 75.00,
    },
    {
        "vendor_id": "VENDOR-005",
        "vendor_name": "Texas Pro Supply",
        "vendor_type": "wholesaler",
        "contact_email": "orders@texasprosupply.example.com",
        "contact_phone": "555-500-5000",
        "website": "https://texasprosupply.example.com",
        "headquarters_city": "Dallas",
        "headquarters_state": "TX",
        "headquarters_country": "USA",
        "headquarters_zip": "75201",
        "latitude": 32.779,
        "longitude": -96.809,
        "reliability_score": 0.85,
        "avg_lead_time_days": 6,
        "min_order_value": 200.00,
    },
]

# ============================================
# Geographic Markets
# ============================================

MARKETS = [
    {
        "market_id": "MARKET-NE-001",
        "region_name": "Northeast",
        "region_code": "NE",
        "country_code": "USA",
        "latitude": 41.5,
        "longitude": -73.5,
        "market_size_tier": "tier_1",
        "population": 55000000,
        "gdp_per_capita": 72000,
        "cost_of_living_index": 1.25,
        "regional_price_multiplier": 1.15,
        "bbox_north": 45.0,
        "bbox_south": 38.0,
        "bbox_east": -67.0,
        "bbox_west": -80.0,
    },
    {
        "market_id": "MARKET-SE-001",
        "region_name": "Southeast",
        "region_code": "SE",
        "country_code": "USA",
        "latitude": 33.5,
        "longitude": -84.0,
        "market_size_tier": "tier_1",
        "population": 65000000,
        "gdp_per_capita": 55000,
        "cost_of_living_index": 0.95,
        "regional_price_multiplier": 0.95,
        "bbox_north": 38.0,
        "bbox_south": 25.0,
        "bbox_east": -75.0,
        "bbox_west": -92.0,
    },
    {
        "market_id": "MARKET-WE-001",
        "region_name": "West",
        "region_code": "WE",
        "country_code": "USA",
        "latitude": 36.0,
        "longitude": -118.0,
        "market_size_tier": "tier_1",
        "population": 50000000,
        "gdp_per_capita": 68000,
        "cost_of_living_index": 1.20,
        "regional_price_multiplier": 1.10,
        "bbox_north": 49.0,
        "bbox_south": 32.0,
        "bbox_east": -102.0,
        "bbox_west": -125.0,
    },
]

# ============================================
# Distribution Centers
# ============================================

DISTRIBUTION_CENTERS = [
    {
        "center_id": "DC-NE-001",
        "market_id": "MARKET-NE-001",
        "vendor_id": "VENDOR-004",
        "center_name": "Northeast Distribution Hub",
        "center_type": "warehouse",
        "city": "Newark",
        "state": "NJ",
        "country": "USA",
        "zip_code": "07102",
        "latitude": 40.735,
        "longitude": -74.172,
        "square_footage": 250000,
        "max_daily_shipments": 5000,
        "service_radius_miles": 200,
    },
    {
        "center_id": "DC-SE-001",
        "market_id": "MARKET-SE-001",
        "vendor_id": "VENDOR-001",
        "center_name": "Southeast Fulfillment Center",
        "center_type": "fulfillment",
        "city": "Charlotte",
        "state": "NC",
        "country": "USA",
        "zip_code": "28202",
        "latitude": 35.227,
        "longitude": -80.843,
        "square_footage": 300000,
        "max_daily_shipments": 7500,
        "service_radius_miles": 250,
    },
    {
        "center_id": "DC-WE-001",
        "market_id": "MARKET-WE-001",
        "vendor_id": "VENDOR-003",
        "center_name": "West Coast Distribution",
        "center_type": "warehouse",
        "city": "Riverside",
        "state": "CA",
        "country": "USA",
        "zip_code": "92501",
        "latitude": 33.953,
        "longitude": -117.396,
        "square_footage": 400000,
        "max_daily_shipments": 10000,
        "service_radius_miles": 300,
    },
]


def generate_sku_id(category: str, index: int) -> str:
    """Generate a unique SKU ID."""
    prefix = category[:3].upper()
    return f"{prefix}-{index:04d}"


def generate_skus() -> list[dict]:
    """Generate SKU data."""
    skus = []
    sku_index = 1

    for category, products in PRODUCT_DATA.items():
        for product_name, min_price, max_price in products:
            # Generate random dimensions
            weight = round(random.uniform(0.5, 50.0), 1)
            length = round(random.uniform(1.0, 96.0), 1) if random.random() > 0.3 else None
            width = round(random.uniform(1.0, 48.0), 1) if length else None
            height = round(random.uniform(0.5, 24.0), 1) if random.random() > 0.5 else None

            sku = {
                "sku_id": generate_sku_id(category, sku_index),
                "product_name": product_name,
                "description": f"High-quality {product_name.lower()} for professional and DIY projects.",
                "category": category,
                "subcategory": None,
                "weight_lbs": weight,
                "length_inches": length,
                "width_inches": width,
                "height_inches": height,
                "unit_of_measure": "each",
                "units_per_case": random.choice([1, 6, 12, 24]) if random.random() > 0.5 else None,
                "primary_supplier_id": random.choice(VENDORS)["vendor_id"],
                "manufacturer": f"{product_name.split()[0]}Co Inc" if random.random() > 0.3 else None,
                "manufacturer_part_number": f"MFG-{random.randint(10000, 99999)}" if random.random() > 0.4 else None,
                "upc_code": f"{random.randint(100000000000, 999999999999)}" if random.random() > 0.5 else None,
            }
            skus.append(sku)
            sku_index += 1

    return skus


def generate_vendor_pricing(skus: list[dict]) -> list[dict]:
    """Generate vendor pricing data."""
    pricing = []
    base_date = datetime.now() - timedelta(days=30)

    for sku in skus:
        category = sku["category"]
        products = PRODUCT_DATA[category]

        # Find base price range for this product
        base_min, base_max = None, None
        for name, pmin, pmax in products:
            if name == sku["product_name"]:
                base_min, base_max = pmin, pmax
                break

        if not base_min:
            continue

        # Generate prices for random subset of vendors (3-5 vendors per SKU)
        num_vendors = random.randint(3, 5)
        selected_vendors = random.sample(VENDORS, num_vendors)

        for vendor in selected_vendors:
            # Each vendor offers this SKU in 1-3 regions
            num_regions = random.randint(1, 3)
            selected_regions = random.sample(MARKETS, num_regions)

            for market in selected_regions:
                # Apply regional multiplier
                regional_mult = market["regional_price_multiplier"]
                base_price = random.uniform(base_min, base_max) * regional_mult

                # Add vendor-specific variation
                vendor_variation = random.uniform(0.95, 1.08)
                final_price = round(base_price * vendor_variation, 2)

                # Generate effective date within last 30 days
                days_ago = random.randint(0, 30)
                effective_date = base_date + timedelta(days=days_ago)

                pricing_record = {
                    "sku_id": sku["sku_id"],
                    "vendor_id": vendor["vendor_id"],
                    "market_id": market["market_id"],
                    "price": final_price,
                    "currency": "USD",
                    "price_per_unit": final_price,
                    "unit_of_measure": sku["unit_of_measure"],
                    "geographic_region": market["region_name"],
                    "effective_date": effective_date.strftime("%Y-%m-%d"),
                    "expiration_date": None,
                    "confidence_score": round(random.uniform(0.75, 0.99), 2),
                    "data_source": random.choice(["api", "csv_import", "manual"]),
                    "is_verified": random.random() > 0.3,
                }
                pricing.append(pricing_record)

    return pricing


def write_csv(data: list[dict], filename: str):
    """Write data to CSV file."""
    if not data:
        return

    filepath = OUTPUT_DIR / filename
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"  Written: {filepath} ({len(data)} records)")


def main():
    """Generate all sample data files."""
    print("Generating sample data for PricePoint Intel...")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate SKUs
    print("Generating SKUs...")
    skus = generate_skus()
    write_csv(skus, "skus.csv")

    # Write vendors
    print("Writing vendors...")
    write_csv(VENDORS, "vendors.csv")

    # Write markets
    print("Writing markets...")
    write_csv(MARKETS, "markets.csv")

    # Write distribution centers
    print("Writing distribution centers...")
    write_csv(DISTRIBUTION_CENTERS, "distribution_centers.csv")

    # Generate pricing
    print("Generating vendor pricing...")
    pricing = generate_vendor_pricing(skus)
    write_csv(pricing, "vendor_pricing.csv")

    # Summary
    print()
    print("=" * 50)
    print("Sample Data Generation Complete")
    print("=" * 50)
    print(f"  SKUs: {len(skus)}")
    print(f"  Vendors: {len(VENDORS)}")
    print(f"  Markets: {len(MARKETS)}")
    print(f"  Distribution Centers: {len(DISTRIBUTION_CENTERS)}")
    print(f"  Pricing Records: {len(pricing)}")
    print()
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
