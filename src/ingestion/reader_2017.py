"""Reader module for 2017 Jakarta ISPU HTML tables (Layout A)."""

from pathlib import Path
from typing import IO, Union
import pandas as pd
from src.ingestion.models import LayoutMismatchError

EXPECTED_COLUMNS_2017 = [
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
]


def read_ispu_2017_html(
    source: Union[str, Path, IO[str], IO[bytes]]
) -> pd.DataFrame:
    """Reads a 2017 Jakarta ISPU HTML file into a pandas DataFrame.

    All columns are preserved as raw strings without type inference,
    preserving exact tokens such as '---', empty cells, and leading zeros.

    Args:
        source: File path, HTML string, or file-like object containing the HTML table.

    Returns:
        pd.DataFrame: Raw DataFrame containing all rows as strings with expected columns.

    Raises:
        LayoutMismatchError: If no table is found or columns do not match 2017 Layout A.
    """
    try:
        tables = pd.read_html(
            source,
            flavor="lxml",
            keep_default_na=False,
        )
    except ValueError as e:
        # pd.read_html raises ValueError if no tables are found
        raise LayoutMismatchError(f"No table found in HTML source: {e}") from e

    if not tables:
        raise LayoutMismatchError("No table found in HTML source.")

    df = tables[0].fillna("").astype(str)

    # Normalize column headers by stripping whitespace and lowercasing
    df.columns = [str(c).strip().lower() for c in df.columns]

    if list(df.columns) != EXPECTED_COLUMNS_2017:
        raise LayoutMismatchError(
            f"Layout mismatch. Expected {EXPECTED_COLUMNS_2017}, got {list(df.columns)}"
        )

    return df
