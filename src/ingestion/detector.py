"""Layout auto-detection and reading module for Jakarta ISPU HTML tables."""

from pathlib import Path
from typing import IO, Sequence, Union
import pandas as pd
from src.ingestion.models import LayoutMismatchError, LayoutType

EXPECTED_LAYOUT_COLUMNS: dict[LayoutType, list[str]] = {
    LayoutType.LAYOUT_A: [
        "periode_data",
        "tanggal",
        "stasiun",
        "pm10",
        "so2",
        "co",
        "o3",
        "no2",
        "max",
        "critical",
        "categori",
    ],
    LayoutType.LAYOUT_A_PM25: [
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
        "categori",
    ],
    LayoutType.LAYOUT_B_NO_PM25: [
        "periode_data",
        "tanggal",
        "pm10",
        "so2",
        "co",
        "o3",
        "no2",
        "max",
        "critical",
        "categori",
        "lokasi_spku",
    ],
    LayoutType.LAYOUT_B: [
        "periode_data",
        "tanggal",
        "pm_10",
        "pm_duakomalima",
        "so2",
        "co",
        "o3",
        "no2",
        "max",
        "critical",
        "categori",
        "lokasi_spku",
    ],
    LayoutType.LAYOUT_C: [
        "periode_data",
        "tanggal",
        "stasiun",
        "pm_sepuluh",
        "pm_duakomalima",
        "sulfur_dioksida",
        "karbon_monoksida",
        "ozon",
        "nitrogen_dioksida",
        "max",
        "parameter_pencemar_kritis",
        "kategori",
    ],
    LayoutType.LAYOUT_C_BULAN: [
        "periode_data",
        "bulan",
        "tanggal",
        "stasiun",
        "pm_sepuluh",
        "pm_duakomalima",
        "sulfur_dioksida",
        "karbon_monoksida",
        "ozon",
        "nitrogen_dioksida",
        "max",
        "parameter_pencemar_kritis",
        "kategori",
    ],
}


def detect_layout(columns: Sequence[str]) -> LayoutType:
    """Identifies the LayoutType matching the given column sequence.

    Column names are normalized (lowercased and stripped of leading/trailing whitespace).
    If the sequence does not match any known layout signature, a LayoutMismatchError is raised.

    Args:
        columns: Sequence of column names to match.

    Returns:
        LayoutType: Identified layout enum.

    Raises:
        LayoutMismatchError: If the columns do not match any known layout signature.
    """
    normalized = [str(c).strip().lower() for c in columns]

    for layout_type, expected_cols in EXPECTED_LAYOUT_COLUMNS.items():
        if normalized == expected_cols:
            return layout_type

    raise LayoutMismatchError(
        f"Unknown layout with columns: {normalized}. "
        f"Registered layout signatures: {[list(cols) for cols in EXPECTED_LAYOUT_COLUMNS.values()]}"
    )


def read_and_detect(
    source: Union[str, Path, IO[str], IO[bytes]]
) -> tuple[LayoutType, pd.DataFrame]:
    """Reads an ISPU HTML table, normalizes headers, and detects its layout.

    All cell values are preserved as raw strings without type inference,
    preserving exact tokens such as '---', empty cells, and leading zeros.

    Args:
        source: File path, HTML string, or file-like object containing the HTML table.

    Returns:
        tuple[LayoutType, pd.DataFrame]: Detected layout type and the raw DataFrame.

    Raises:
        LayoutMismatchError: If no HTML table is found or the table layout is unknown.
    """
    try:
        tables = pd.read_html(
            source,
            flavor="lxml",
            keep_default_na=False,
        )
    except ValueError as e:
        raise LayoutMismatchError(f"No table found in HTML source: {e}") from e

    if not tables:
        raise LayoutMismatchError("No table found in HTML source.")

    df = tables[0].fillna("").astype(str)
    df.columns = [str(c).strip().lower() for c in df.columns]

    layout = detect_layout(df.columns)
    return layout, df
