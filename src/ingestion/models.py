"""Data models and exception classes for ISPU ingestion pipeline."""

from dataclasses import dataclass
from enum import Enum
import pandas as pd


class LayoutType(str, Enum):
    """Enumeration of known ISPU table column layouts."""

    LAYOUT_A = "layout_a"  # 2016, 2017, 2018, 2020: 11 cols, station at col 3, no PM2.5
    LAYOUT_A_PM25 = "layout_a_pm25"  # 2021: 12 cols, station at col 3, includes pm25
    LAYOUT_B_NO_PM25 = "layout_b_no_pm25"  # 2019: 11 cols, lokasi_spku at end, no PM2.5
    LAYOUT_B = "layout_b"  # 2022: 12 cols, lokasi_spku at end, includes pm_duakomalima
    LAYOUT_C = "layout_c"  # 2023: 12 cols, station at col 3, Indonesian pollutant names
    LAYOUT_C_BULAN = "layout_c_bulan"  # 2024–2025: 13 cols, includes bulan and day-of-month


class LayoutMismatchError(ValueError):
    """Raised when the columns or structure of an ISPU file do not match the expected layout."""

    pass


@dataclass(frozen=True)
class ValidationResult:
    """Encapsulates the output of row-level validation.

    Attributes:
        valid: DataFrame containing rows that passed all validation rules.
        quarantined: DataFrame containing rows that failed validation,
            augmented with a 'quarantine_reason' column.
    """

    valid: pd.DataFrame
    quarantined: pd.DataFrame
