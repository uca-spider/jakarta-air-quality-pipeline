"""Schema harmonization module for Jakarta ISPU DataFrames."""

from typing import Mapping
import pandas as pd
from src.ingestion.models import LayoutType

CANONICAL_COLUMNS: list[str] = [
    "periode_data",
    "tanggal",
    "stasiun",
    "pm10",
    "pm25",
    "so2",
    "co",
    "o3",
    "no2",
    "max",
    "critical",
    "kategori",
]

QUARANTINE_COLUMNS: list[str] = CANONICAL_COLUMNS + ["quarantine_reason"]

# Column rename dictionaries per layout
COLUMN_MAPPINGS: dict[LayoutType, Mapping[str, str]] = {
    LayoutType.LAYOUT_A: {
        "categori": "kategori",
    },
    LayoutType.LAYOUT_A_PM25: {
        "categori": "kategori",
    },
    LayoutType.LAYOUT_B_NO_PM25: {
        "lokasi_spku": "stasiun",
        "categori": "kategori",
    },
    LayoutType.LAYOUT_B: {
        "lokasi_spku": "stasiun",
        "pm_10": "pm10",
        "pm_duakomalima": "pm25",
        "categori": "kategori",
    },
    LayoutType.LAYOUT_C: {
        "pm_sepuluh": "pm10",
        "pm_duakomalima": "pm25",
        "sulfur_dioksida": "so2",
        "karbon_monoksida": "co",
        "ozon": "o3",
        "nitrogen_dioksida": "no2",
        "parameter_pencemar_kritis": "critical",
    },
    LayoutType.LAYOUT_C_BULAN: {
        "pm_sepuluh": "pm10",
        "pm_duakomalima": "pm25",
        "sulfur_dioksida": "so2",
        "karbon_monoksida": "co",
        "ozon": "o3",
        "nitrogen_dioksida": "no2",
        "parameter_pencemar_kritis": "critical",
    },
}


def harmonize_layout(
    df: pd.DataFrame,
    layout: LayoutType,
    is_quarantine: bool = False,
) -> pd.DataFrame:
    """Harmonizes an ISPU DataFrame to the standard CANONICAL_COLUMNS or QUARANTINE_COLUMNS.

    - Renames layout-specific column names (e.g. pm_sepuluh -> pm10, lokasi_spku -> stasiun).
    - Inserts an empty string column for pm25 if not present in the layout (2016-2020, 2019).
    - Drops layout-specific temporary columns (e.g. 'bulan').
    - Ensures identical column order matching CANONICAL_COLUMNS (or QUARANTINE_COLUMNS).
    - Preserves all raw string tokens in the cells.

    Args:
        df: Validated DataFrame.
        layout: Identified LayoutType.
        is_quarantine: Whether this is a quarantined DataFrame (appends quarantine_reason).

    Returns:
        pd.DataFrame: Harmonized DataFrame with standard columns in order.
    """
    target_columns = QUARANTINE_COLUMNS if is_quarantine else CANONICAL_COLUMNS
    if df.empty:
        return pd.DataFrame(columns=target_columns)

    harmonized = df.copy()
    reason = harmonized.get("quarantine_reason") if is_quarantine else None

    # Step 1: Apply column renaming
    mapping = COLUMN_MAPPINGS.get(layout, {})
    if mapping:
        harmonized = harmonized.rename(columns=mapping)

    # Step 2: Ensure pm25 exists
    if "pm25" not in harmonized.columns:
        harmonized["pm25"] = ""

    # Step 3: Reindex/select canonical columns
    for col in CANONICAL_COLUMNS:
        if col not in harmonized.columns:
            harmonized[col] = ""

    if is_quarantine:
        harmonized = harmonized[CANONICAL_COLUMNS].copy()
        harmonized["quarantine_reason"] = reason if reason is not None else ""
        return harmonized[QUARANTINE_COLUMNS]

    return harmonized[CANONICAL_COLUMNS]
