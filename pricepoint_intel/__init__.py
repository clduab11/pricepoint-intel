"""
PricePoint Intel - SKU-Level Competitive Intelligence Platform

A research-driven competitive intelligence system that transforms geopolitical
risk analysis frameworks into procurement intelligence.
"""

from dataclasses import dataclass, field
from typing import Any

from pricepoint_intel.intelligence_engine.core import IntelligenceEngine
from pricepoint_intel.models.results import QueryResults

__version__ = "0.1.0"
__all__ = ["IntelligenceEngine", "QueryResults", "__version__"]
