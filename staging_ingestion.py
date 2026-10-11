"""Load raw Uber bookings into a lightly normalized staging CSV."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
RAW_PATH = PROJECT_ROOT / "Data" / "Raw" / "uber.csv"
STAGING_PATH = PROJECT_ROOT / "Data" / "Staging" / "uber_staging.csv"

REQUIRED_COLUMNS = {
    "Booking ID",
    "Date",
    "Time",
    "Booking Status",
    "Vehicle Type",
    "Pickup Location",
    "Drop Location",
    "Booking Value",
    "Ride Distance",
}

LOGGER = logging.getLogger(__name__)


def load_raw_data(path: Path = RAW_PATH) -> pd.DataFrame:
    """Read the source CSV as text to preserve raw values for downstream SSIS."""
    if not path.is_file():
        raise FileNotFoundError(f"Source CSV not found: {path}")

    return pd.read_csv(path, dtype=str, keep_default_na=False)


def validate_schema(data: pd.DataFrame) -> None:
    """Ensure the source includes the columns needed by the ingestion contract."""
    missing_columns = sorted(REQUIRED_COLUMNS.difference(data.columns))
    if missing_columns:
        LOGGER.warning("Source is missing required columns: %s", missing_columns)
        raise ValueError(f"Invalid source schema; missing columns: {missing_columns}")


def clean_raw_strings(data: pd.DataFrame) -> pd.DataFrame:
    """Strip surrounding whitespace from text fields without applying business rules."""
    cleaned = data.copy()
    string_columns = cleaned.select_dtypes(include=["object", "string"]).columns
    cleaned[string_columns] = cleaned[string_columns].apply(lambda column: column.str.strip())
    return cleaned


def add_audit_metadata(data: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    """Add batch timestamp and source filename to every staged row."""
    staged = data.copy()
    staged["ingestion_timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    staged["source_file_name"] = source_path.name
    return staged


def export_staging(data: pd.DataFrame, path: Path = STAGING_PATH) -> None:
    """Write staged records, creating the destination directory when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False, encoding="utf-8")
    LOGGER.info("Exported %s rows and %s columns to %s", len(data), len(data.columns), path)


def run_pipeline(
    source_path: Path = RAW_PATH,
    staging_path: Path = STAGING_PATH,
) -> pd.DataFrame:
    """Run source loading, structural checks, raw cleanup, and staging export."""
    LOGGER.info("Loading source file: %s", source_path)
    raw_data = load_raw_data(source_path)
    validate_schema(raw_data)
    LOGGER.info("Loaded %s rows and %s columns", len(raw_data), len(raw_data.columns))

    staged_data = clean_raw_strings(raw_data)
    staged_data = add_audit_metadata(staged_data, source_path)
    export_staging(staged_data, staging_path)
    return staged_data


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        run_pipeline()
    except (FileNotFoundError, pd.errors.ParserError, ValueError):
        LOGGER.exception("Staging ingestion failed")
        raise


if __name__ == "__main__":
    main()