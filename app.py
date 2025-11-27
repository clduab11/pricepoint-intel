#!/usr/bin/env python3
"""
PricePoint Intel - Main Application Entry Point

This module provides the main entry point for the PricePoint Intel application.
It can run either the FastAPI REST API or the Dash research dashboard.

Usage:
    python app.py             # Run Dash dashboard (default)
    python app.py --api       # Run FastAPI server
    python app.py --both      # Run both servers
"""

import argparse
import os
import sys
from threading import Thread

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_dash_app(host: str = "127.0.0.1", port: int = 8050, debug: bool = True):
    """Run the Dash research dashboard."""
    from pricepoint_intel.dashboard.app import create_dash_app

    app = create_dash_app()
    app.run_server(host=host, port=port, debug=debug)


def run_fastapi_app(host: str = "127.0.0.1", port: int = 8000):
    """Run the FastAPI REST API server."""
    import uvicorn

    from pricepoint_intel.api.app import app

    uvicorn.run(app, host=host, port=port)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PricePoint Intel - SKU-Level Competitive Intelligence Platform"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Run FastAPI REST API server",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Run both Dash dashboard and FastAPI server",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8050")),
        help="Port for Dash dashboard (default: 8050)",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="Port for FastAPI server (default: 8000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.getenv("DEBUG", "True").lower() == "true",
        help="Enable debug mode",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  PricePoint Intel - Competitive Intelligence Platform")
    print("=" * 60)

    if args.both:
        print(f"\n🚀 Starting Dash Dashboard on http://{args.host}:{args.port}")
        print(f"🚀 Starting FastAPI Server on http://{args.host}:{args.api_port}")

        # Run FastAPI in a separate thread
        api_thread = Thread(
            target=run_fastapi_app,
            kwargs={"host": args.host, "port": args.api_port},
            daemon=True,
        )
        api_thread.start()

        # Run Dash in main thread
        run_dash_app(host=args.host, port=args.port, debug=args.debug)

    elif args.api:
        print(f"\n🚀 Starting FastAPI Server on http://{args.host}:{args.api_port}")
        print(f"📚 API Documentation at http://{args.host}:{args.api_port}/docs")
        run_fastapi_app(host=args.host, port=args.api_port)

    else:
        print(f"\n🚀 Starting Dash Dashboard on http://{args.host}:{args.port}")
        print("   Use --api flag to run FastAPI server instead")
        print("   Use --both flag to run both servers")
        run_dash_app(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
