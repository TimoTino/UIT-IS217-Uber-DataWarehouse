"""Rebuild the clean dataset from the project root.

Run from any directory with: ``python preprocess.py``.
The raw CSV is never modified.
"""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW_FILE = ROOT / "Data" / "Raw" / "uber.csv"
CLEAN_FILE = ROOT / "Data" / "Clean" / "uber_cleaned.csv"

REQUIRED_COLUMNS = {
    "Booking ID", "Date", "Time", "Booking Status", "Vehicle Type",
    "Pickup Location", "Drop Location", "Booking Value", "Ride Distance",
}


def build_clean_file() -> tuple[int, int]:
    if not RAW_FILE.is_file():
        raise FileNotFoundError(f"Không tìm thấy raw file: {RAW_FILE}")

    raw = pd.read_csv(RAW_FILE, dtype="string", keep_default_na=False)
    missing = sorted(REQUIRED_COLUMNS - set(raw.columns))
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc: {missing}")

    clean = raw.drop_duplicates().copy()
    clean = clean.rename(columns={"Avg VTAT": "VTAT", "Avg CTAT": "CTAT"})

    # Chuẩn hóa text và giá trị null; không thay đổi file raw.
    for column in clean.columns:
        clean[column] = (
            clean[column].astype("string").str.strip()
            .str.replace(r'^"+|"+$', "", regex=True)
            .replace("", pd.NA)
            .fillna("NA")
        )

    # Các trường đo lường được xuất dưới dạng số để SSIS/SQL nhận đúng kiểu.
    numeric_columns = [
        "Booking Value", "Ride Distance", "Driver Ratings", "Customer Rating",
        "VTAT", "CTAT", "Cancelled Rides by Customer",
        "Cancelled Rides by Driver", "Incomplete Rides",
    ]
    for column in numeric_columns:
        if column in clean:
            clean[column] = pd.to_numeric(clean[column].replace("NA", pd.NA), errors="coerce")
            clean[column] = clean[column].fillna(0)

    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(CLEAN_FILE, index=False, encoding="utf-8")
    return len(raw), len(clean)


if __name__ == "__main__":
    before, after = build_clean_file()
    print(f"Raw rows: {before:,}")
    print(f"Clean rows: {after:,}")
    print(f"Removed duplicates: {before - after:,}")
