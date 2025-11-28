"""CSV and Excel data importer for bulk vendor pricing data.

Supports importing SKUs, pricing, vendors, and market data from flat files.
"""

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Callable, Generator, Optional, TextIO, Type, Union
import structlog

from pricepoint_intel.database.models import (
    SKU,
    Vendor,
    VendorPricing,
    GeographicMarket,
    DistributionCenter,
)
from pricepoint_intel.database.connection import session_scope, DatabaseConfig
from pricepoint_intel.ingestion.validators import (
    DataValidator,
    SKUValidator,
    PricingValidator,
    MarketValidator,
    VendorValidator,
    ValidationResult,
    ValidationSeverity,
)

logger = structlog.get_logger(__name__)


@dataclass
class ImportStats:
    """Statistics from an import operation."""

    total_rows: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    warnings: int = 0
    errors: list = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return (self.successful / self.total_rows) * 100

    def to_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "success_rate": f"{self.success_rate:.2f}%",
            "duration_seconds": self.duration_seconds,
            "errors": self.errors[:100],  # Limit errors in response
        }


@dataclass
class ImportConfig:
    """Configuration for import operations."""

    batch_size: int = 100
    skip_header: bool = True
    delimiter: str = ","
    encoding: str = "utf-8"
    on_error: str = "continue"  # continue, stop, rollback
    update_existing: bool = True  # Update if record exists
    dry_run: bool = False  # Validate only, don't write
    progress_callback: Optional[Callable[[int, int], None]] = None


class CSVImporter:
    """Import data from CSV files."""

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
        import_config: Optional[ImportConfig] = None,
    ):
        """Initialize CSV importer.

        Args:
            db_config: Database configuration (defaults to env)
            import_config: Import configuration options
        """
        self.db_config = db_config
        self.config = import_config or ImportConfig()

    def _read_csv(
        self,
        file_path: Union[str, Path, TextIO, BinaryIO],
    ) -> Generator[dict, None, None]:
        """Read CSV file and yield rows as dictionaries.

        Args:
            file_path: Path to CSV file or file-like object

        Yields:
            Dictionary for each row
        """
        if isinstance(file_path, (str, Path)):
            with open(file_path, "r", encoding=self.config.encoding) as f:
                yield from self._parse_csv(f)
        elif hasattr(file_path, "read"):
            # File-like object
            content = file_path.read()
            if isinstance(content, bytes):
                content = content.decode(self.config.encoding)
            yield from self._parse_csv(io.StringIO(content))
        else:
            raise ValueError(f"Unsupported file type: {type(file_path)}")

    def _parse_csv(self, file_obj: TextIO) -> Generator[dict, None, None]:
        """Parse CSV content from file object.

        Args:
            file_obj: File object containing CSV data

        Yields:
            Dictionary for each row
        """
        reader = csv.DictReader(file_obj, delimiter=self.config.delimiter)
        for row in reader:
            # Clean up keys and values
            cleaned = {
                k.strip().lower().replace(" ", "_"): v.strip() if v else None
                for k, v in row.items()
                if k
            }
            yield cleaned

    def import_skus(
        self,
        file_path: Union[str, Path, TextIO, BinaryIO],
    ) -> ImportStats:
        """Import SKU data from CSV file.

        Args:
            file_path: Path to CSV file or file-like object

        Returns:
            ImportStats with operation results
        """
        validator = SKUValidator()
        stats = ImportStats(start_time=datetime.utcnow())

        logger.info("Starting SKU import", file=str(file_path))

        batch = []
        with session_scope(self.db_config) as session:
            for row_idx, row in enumerate(self._read_csv(file_path)):
                stats.total_rows += 1

                # Validate row
                result = validator.validate(row, row_index=row_idx)

                if not result.is_valid:
                    stats.failed += 1
                    stats.errors.extend([e.to_dict() for e in result.errors])
                    if self.config.on_error == "stop":
                        break
                    continue

                if result.warnings:
                    stats.warnings += len(result.warnings)

                if self.config.dry_run:
                    stats.successful += 1
                    continue

                # Check for existing SKU
                if self.config.update_existing:
                    existing = (
                        session.query(SKU)
                        .filter(SKU.sku_id == result.cleaned_data["sku_id"])
                        .first()
                    )
                    if existing:
                        # Update existing
                        for key, value in result.cleaned_data.items():
                            if key != "sku_id":
                                setattr(existing, key, value)
                        stats.successful += 1
                        continue

                # Create new SKU
                sku = SKU(**result.cleaned_data)
                batch.append(sku)

                # Batch insert
                if len(batch) >= self.config.batch_size:
                    session.add_all(batch)
                    session.flush()
                    stats.successful += len(batch)
                    batch = []

                # Progress callback
                if self.config.progress_callback:
                    self.config.progress_callback(stats.total_rows, stats.successful)

            # Insert remaining batch
            if batch:
                session.add_all(batch)
                session.flush()
                stats.successful += len(batch)

        stats.end_time = datetime.utcnow()
        logger.info(
            "SKU import complete",
            total=stats.total_rows,
            successful=stats.successful,
            failed=stats.failed,
        )
        return stats

    def import_pricing(
        self,
        file_path: Union[str, Path, TextIO, BinaryIO],
    ) -> ImportStats:
        """Import vendor pricing data from CSV file.

        Args:
            file_path: Path to CSV file or file-like object

        Returns:
            ImportStats with operation results
        """
        validator = PricingValidator()
        stats = ImportStats(start_time=datetime.utcnow())

        logger.info("Starting pricing import", file=str(file_path))

        batch = []
        with session_scope(self.db_config) as session:
            for row_idx, row in enumerate(self._read_csv(file_path)):
                stats.total_rows += 1

                # Validate row
                result = validator.validate(row, row_index=row_idx)

                if not result.is_valid:
                    stats.failed += 1
                    stats.errors.extend([e.to_dict() for e in result.errors])
                    if self.config.on_error == "stop":
                        break
                    continue

                if result.warnings:
                    stats.warnings += len(result.warnings)

                if self.config.dry_run:
                    stats.successful += 1
                    continue

                # Check if SKU exists
                sku_exists = (
                    session.query(SKU.sku_id)
                    .filter(SKU.sku_id == result.cleaned_data["sku_id"])
                    .first()
                )
                if not sku_exists:
                    stats.skipped += 1
                    stats.errors.append({
                        "field": "sku_id",
                        "message": f"SKU not found: {result.cleaned_data['sku_id']}",
                        "row_index": row_idx,
                    })
                    continue

                # Check if vendor exists
                vendor_exists = (
                    session.query(Vendor.vendor_id)
                    .filter(Vendor.vendor_id == result.cleaned_data["vendor_id"])
                    .first()
                )
                if not vendor_exists:
                    stats.skipped += 1
                    stats.errors.append({
                        "field": "vendor_id",
                        "message": f"Vendor not found: {result.cleaned_data['vendor_id']}",
                        "row_index": row_idx,
                    })
                    continue

                # Update existing or create new
                if self.config.update_existing:
                    existing = (
                        session.query(VendorPricing)
                        .filter(
                            VendorPricing.sku_id == result.cleaned_data["sku_id"],
                            VendorPricing.vendor_id == result.cleaned_data["vendor_id"],
                            VendorPricing.geographic_region
                            == result.cleaned_data.get("geographic_region"),
                        )
                        .first()
                    )
                    if existing:
                        for key, value in result.cleaned_data.items():
                            setattr(existing, key, value)
                        stats.successful += 1
                        continue

                # Create new pricing record
                pricing = VendorPricing(**result.cleaned_data)
                batch.append(pricing)

                if len(batch) >= self.config.batch_size:
                    session.add_all(batch)
                    session.flush()
                    stats.successful += len(batch)
                    batch = []

                if self.config.progress_callback:
                    self.config.progress_callback(stats.total_rows, stats.successful)

            if batch:
                session.add_all(batch)
                session.flush()
                stats.successful += len(batch)

        stats.end_time = datetime.utcnow()
        logger.info(
            "Pricing import complete",
            total=stats.total_rows,
            successful=stats.successful,
            failed=stats.failed,
        )
        return stats

    def import_vendors(
        self,
        file_path: Union[str, Path, TextIO, BinaryIO],
    ) -> ImportStats:
        """Import vendor data from CSV file.

        Args:
            file_path: Path to CSV file or file-like object

        Returns:
            ImportStats with operation results
        """
        validator = VendorValidator()
        stats = ImportStats(start_time=datetime.utcnow())

        logger.info("Starting vendor import", file=str(file_path))

        batch = []
        with session_scope(self.db_config) as session:
            for row_idx, row in enumerate(self._read_csv(file_path)):
                stats.total_rows += 1

                result = validator.validate(row, row_index=row_idx)

                if not result.is_valid:
                    stats.failed += 1
                    stats.errors.extend([e.to_dict() for e in result.errors])
                    if self.config.on_error == "stop":
                        break
                    continue

                if result.warnings:
                    stats.warnings += len(result.warnings)

                if self.config.dry_run:
                    stats.successful += 1
                    continue

                if self.config.update_existing:
                    existing = (
                        session.query(Vendor)
                        .filter(Vendor.vendor_id == result.cleaned_data["vendor_id"])
                        .first()
                    )
                    if existing:
                        for key, value in result.cleaned_data.items():
                            if key != "vendor_id":
                                setattr(existing, key, value)
                        stats.successful += 1
                        continue

                vendor = Vendor(**result.cleaned_data)
                batch.append(vendor)

                if len(batch) >= self.config.batch_size:
                    session.add_all(batch)
                    session.flush()
                    stats.successful += len(batch)
                    batch = []

                if self.config.progress_callback:
                    self.config.progress_callback(stats.total_rows, stats.successful)

            if batch:
                session.add_all(batch)
                session.flush()
                stats.successful += len(batch)

        stats.end_time = datetime.utcnow()
        logger.info(
            "Vendor import complete",
            total=stats.total_rows,
            successful=stats.successful,
            failed=stats.failed,
        )
        return stats

    def import_markets(
        self,
        file_path: Union[str, Path, TextIO, BinaryIO],
    ) -> ImportStats:
        """Import geographic market data from CSV file.

        Args:
            file_path: Path to CSV file or file-like object

        Returns:
            ImportStats with operation results
        """
        validator = MarketValidator()
        stats = ImportStats(start_time=datetime.utcnow())

        logger.info("Starting market import", file=str(file_path))

        batch = []
        with session_scope(self.db_config) as session:
            for row_idx, row in enumerate(self._read_csv(file_path)):
                stats.total_rows += 1

                result = validator.validate(row, row_index=row_idx)

                if not result.is_valid:
                    stats.failed += 1
                    stats.errors.extend([e.to_dict() for e in result.errors])
                    if self.config.on_error == "stop":
                        break
                    continue

                if result.warnings:
                    stats.warnings += len(result.warnings)

                if self.config.dry_run:
                    stats.successful += 1
                    continue

                if self.config.update_existing:
                    existing = (
                        session.query(GeographicMarket)
                        .filter(
                            GeographicMarket.market_id == result.cleaned_data["market_id"]
                        )
                        .first()
                    )
                    if existing:
                        for key, value in result.cleaned_data.items():
                            if key != "market_id":
                                setattr(existing, key, value)
                        stats.successful += 1
                        continue

                market = GeographicMarket(**result.cleaned_data)
                batch.append(market)

                if len(batch) >= self.config.batch_size:
                    session.add_all(batch)
                    session.flush()
                    stats.successful += len(batch)
                    batch = []

                if self.config.progress_callback:
                    self.config.progress_callback(stats.total_rows, stats.successful)

            if batch:
                session.add_all(batch)
                session.flush()
                stats.successful += len(batch)

        stats.end_time = datetime.utcnow()
        logger.info(
            "Market import complete",
            total=stats.total_rows,
            successful=stats.successful,
            failed=stats.failed,
        )
        return stats


class ExcelImporter(CSVImporter):
    """Import data from Excel files (.xlsx, .xls)."""

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
        import_config: Optional[ImportConfig] = None,
    ):
        """Initialize Excel importer.

        Args:
            db_config: Database configuration
            import_config: Import configuration options
        """
        super().__init__(db_config, import_config)

    def _read_excel(
        self,
        file_path: Union[str, Path, BinaryIO],
        sheet_name: Optional[str] = None,
    ) -> Generator[dict, None, None]:
        """Read Excel file and yield rows as dictionaries.

        Args:
            file_path: Path to Excel file or file-like object
            sheet_name: Optional sheet name (defaults to first sheet)

        Yields:
            Dictionary for each row
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel import: pip install pandas openpyxl")

        # Read Excel file
        if isinstance(file_path, (str, Path)):
            df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name or 0)

        # Clean column names
        df.columns = [
            str(c).strip().lower().replace(" ", "_") for c in df.columns
        ]

        # Convert to dictionaries
        for _, row in df.iterrows():
            yield {
                k: (None if pd.isna(v) else v)
                for k, v in row.to_dict().items()
            }

    def import_skus_excel(
        self,
        file_path: Union[str, Path, BinaryIO],
        sheet_name: Optional[str] = None,
    ) -> ImportStats:
        """Import SKU data from Excel file.

        Args:
            file_path: Path to Excel file
            sheet_name: Optional sheet name

        Returns:
            ImportStats with operation results
        """
        validator = SKUValidator()
        stats = ImportStats(start_time=datetime.utcnow())

        logger.info("Starting SKU import from Excel", file=str(file_path))

        batch = []
        with session_scope(self.db_config) as session:
            for row_idx, row in enumerate(self._read_excel(file_path, sheet_name)):
                stats.total_rows += 1

                result = validator.validate(row, row_index=row_idx)

                if not result.is_valid:
                    stats.failed += 1
                    stats.errors.extend([e.to_dict() for e in result.errors])
                    if self.config.on_error == "stop":
                        break
                    continue

                if result.warnings:
                    stats.warnings += len(result.warnings)

                if self.config.dry_run:
                    stats.successful += 1
                    continue

                if self.config.update_existing:
                    existing = (
                        session.query(SKU)
                        .filter(SKU.sku_id == result.cleaned_data["sku_id"])
                        .first()
                    )
                    if existing:
                        for key, value in result.cleaned_data.items():
                            if key != "sku_id":
                                setattr(existing, key, value)
                        stats.successful += 1
                        continue

                sku = SKU(**result.cleaned_data)
                batch.append(sku)

                if len(batch) >= self.config.batch_size:
                    session.add_all(batch)
                    session.flush()
                    stats.successful += len(batch)
                    batch = []

            if batch:
                session.add_all(batch)
                session.flush()
                stats.successful += len(batch)

        stats.end_time = datetime.utcnow()
        logger.info(
            "Excel SKU import complete",
            total=stats.total_rows,
            successful=stats.successful,
        )
        return stats

    def import_pricing_excel(
        self,
        file_path: Union[str, Path, BinaryIO],
        sheet_name: Optional[str] = None,
    ) -> ImportStats:
        """Import pricing data from Excel file.

        Args:
            file_path: Path to Excel file
            sheet_name: Optional sheet name

        Returns:
            ImportStats with operation results
        """
        validator = PricingValidator()
        stats = ImportStats(start_time=datetime.utcnow())

        logger.info("Starting pricing import from Excel", file=str(file_path))

        batch = []
        with session_scope(self.db_config) as session:
            for row_idx, row in enumerate(self._read_excel(file_path, sheet_name)):
                stats.total_rows += 1

                result = validator.validate(row, row_index=row_idx)

                if not result.is_valid:
                    stats.failed += 1
                    stats.errors.extend([e.to_dict() for e in result.errors])
                    if self.config.on_error == "stop":
                        break
                    continue

                if result.warnings:
                    stats.warnings += len(result.warnings)

                if self.config.dry_run:
                    stats.successful += 1
                    continue

                # Check references
                sku_exists = (
                    session.query(SKU.sku_id)
                    .filter(SKU.sku_id == result.cleaned_data["sku_id"])
                    .first()
                )
                if not sku_exists:
                    stats.skipped += 1
                    continue

                vendor_exists = (
                    session.query(Vendor.vendor_id)
                    .filter(Vendor.vendor_id == result.cleaned_data["vendor_id"])
                    .first()
                )
                if not vendor_exists:
                    stats.skipped += 1
                    continue

                if self.config.update_existing:
                    existing = (
                        session.query(VendorPricing)
                        .filter(
                            VendorPricing.sku_id == result.cleaned_data["sku_id"],
                            VendorPricing.vendor_id == result.cleaned_data["vendor_id"],
                        )
                        .first()
                    )
                    if existing:
                        for key, value in result.cleaned_data.items():
                            setattr(existing, key, value)
                        stats.successful += 1
                        continue

                pricing = VendorPricing(**result.cleaned_data)
                batch.append(pricing)

                if len(batch) >= self.config.batch_size:
                    session.add_all(batch)
                    session.flush()
                    stats.successful += len(batch)
                    batch = []

            if batch:
                session.add_all(batch)
                session.flush()
                stats.successful += len(batch)

        stats.end_time = datetime.utcnow()
        logger.info(
            "Excel pricing import complete",
            total=stats.total_rows,
            successful=stats.successful,
        )
        return stats


class BulkImporter:
    """Orchestrate bulk import operations across multiple data types."""

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
        import_config: Optional[ImportConfig] = None,
    ):
        """Initialize bulk importer.

        Args:
            db_config: Database configuration
            import_config: Import configuration options
        """
        self.csv_importer = CSVImporter(db_config, import_config)
        self.excel_importer = ExcelImporter(db_config, import_config)
        self.db_config = db_config

    def import_all(
        self,
        vendors_file: Optional[Union[str, Path]] = None,
        markets_file: Optional[Union[str, Path]] = None,
        skus_file: Optional[Union[str, Path]] = None,
        pricing_file: Optional[Union[str, Path]] = None,
    ) -> dict[str, ImportStats]:
        """Import all data types in the correct order.

        Order: vendors -> markets -> SKUs -> pricing

        Args:
            vendors_file: Path to vendors CSV/Excel
            markets_file: Path to markets CSV/Excel
            skus_file: Path to SKUs CSV/Excel
            pricing_file: Path to pricing CSV/Excel

        Returns:
            Dictionary of import stats by data type
        """
        results = {}

        # Import vendors first (needed for pricing)
        if vendors_file:
            logger.info("Importing vendors...")
            if str(vendors_file).endswith((".xlsx", ".xls")):
                results["vendors"] = self.excel_importer.import_skus_excel(vendors_file)
            else:
                results["vendors"] = self.csv_importer.import_vendors(vendors_file)

        # Import markets
        if markets_file:
            logger.info("Importing markets...")
            results["markets"] = self.csv_importer.import_markets(markets_file)

        # Import SKUs (needed for pricing)
        if skus_file:
            logger.info("Importing SKUs...")
            if str(skus_file).endswith((".xlsx", ".xls")):
                results["skus"] = self.excel_importer.import_skus_excel(skus_file)
            else:
                results["skus"] = self.csv_importer.import_skus(skus_file)

        # Import pricing (requires vendors and SKUs)
        if pricing_file:
            logger.info("Importing pricing...")
            if str(pricing_file).endswith((".xlsx", ".xls")):
                results["pricing"] = self.excel_importer.import_pricing_excel(pricing_file)
            else:
                results["pricing"] = self.csv_importer.import_pricing(pricing_file)

        return results

    def validate_files(
        self,
        vendors_file: Optional[Union[str, Path]] = None,
        markets_file: Optional[Union[str, Path]] = None,
        skus_file: Optional[Union[str, Path]] = None,
        pricing_file: Optional[Union[str, Path]] = None,
    ) -> dict[str, ImportStats]:
        """Validate all files without importing (dry run).

        Args:
            vendors_file: Path to vendors CSV/Excel
            markets_file: Path to markets CSV/Excel
            skus_file: Path to SKUs CSV/Excel
            pricing_file: Path to pricing CSV/Excel

        Returns:
            Dictionary of validation stats by data type
        """
        # Create dry-run importers
        dry_run_config = ImportConfig(dry_run=True)
        csv_importer = CSVImporter(self.db_config, dry_run_config)
        excel_importer = ExcelImporter(self.db_config, dry_run_config)

        results = {}

        if vendors_file:
            if str(vendors_file).endswith((".xlsx", ".xls")):
                results["vendors"] = excel_importer.import_skus_excel(vendors_file)
            else:
                results["vendors"] = csv_importer.import_vendors(vendors_file)

        if markets_file:
            results["markets"] = csv_importer.import_markets(markets_file)

        if skus_file:
            if str(skus_file).endswith((".xlsx", ".xls")):
                results["skus"] = excel_importer.import_skus_excel(skus_file)
            else:
                results["skus"] = csv_importer.import_skus(skus_file)

        if pricing_file:
            if str(pricing_file).endswith((".xlsx", ".xls")):
                results["pricing"] = excel_importer.import_pricing_excel(pricing_file)
            else:
                results["pricing"] = csv_importer.import_pricing(pricing_file)

        return results
