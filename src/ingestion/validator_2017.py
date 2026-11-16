"""Validator module for 2017 Jakarta ISPU data."""

import re
import pandas as pd
from src.ingestion.models import ValidationResult

# Regex matching station prefix DKI1 through DKI5 followed by word boundary
STATION_PATTERN = re.compile(r"^DKI[1-5]\b")


def validate_ispu_2017(df: pd.DataFrame) -> ValidationResult:
    """Validates raw 2017 ISPU DataFrame and segregates rows into valid and quarantined.

    Validation rules applied (in order of priority):
    1. MISSING_OR_EMPTY_STATION: Station is empty string or only whitespace.
    2. INVALID_STATION_CODE: Station does not start with DKI1 through DKI5.
       (Catches numeric shifted columns such as March 2020 rows).
    3. INVALID_DATE_FORMAT: Date cannot be parsed as a valid calendar date in YYYY-MM-DD.
    4. DATE_PERIOD_MISMATCH: The YYYYMM of the date does not match periode_data.

    Args:
        df: Raw DataFrame containing 2017 ISPU columns as strings.

    Returns:
        ValidationResult: Dataclass containing:
            - valid: DataFrame with rows that passed all checks.
            - quarantined: DataFrame with failed rows and an added 'quarantine_reason' column.
    """
    if df.empty:
        empty_quarantine = df.copy()
        empty_quarantine["quarantine_reason"] = pd.Series(dtype=str)
        return ValidationResult(valid=df.copy(), quarantined=empty_quarantine)

    reasons = pd.Series(None, index=df.index, dtype=object)

    stasiun_clean = df["stasiun"].fillna("").astype(str).str.strip()
    periode_clean = df["periode_data"].fillna("").astype(str).str.strip()
    tanggal_series = df["tanggal"].fillna("").astype(str).str.strip()

    # Rule 1: Missing or empty station
    is_empty_station = stasiun_clean == ""
    reasons.loc[is_empty_station] = "MISSING_OR_EMPTY_STATION"

    # Rule 2: Invalid station code (e.g. numeric "73", unknown station)
    matches_station_code = stasiun_clean.apply(
        lambda s: bool(STATION_PATTERN.match(s))
    )
    is_invalid_station = ~is_empty_station & ~matches_station_code
    reasons.loc[is_invalid_station & reasons.isna()] = "INVALID_STATION_CODE"

    # Rule 3: Invalid date format (strictly YYYY-MM-DD)
    parsed_dates = pd.to_datetime(
        tanggal_series, format="%Y-%m-%d", errors="coerce"
    )
    is_invalid_date = parsed_dates.isna()
    reasons.loc[is_invalid_date & reasons.isna()] = "INVALID_DATE_FORMAT"

    # Rule 4: Date vs periode_data mismatch (e.g. date in Feb 2017 but periode_data is 201701)
    valid_dates_mask = ~is_invalid_date
    date_period = parsed_dates.dt.strftime("%Y%m")
    is_period_mismatch = valid_dates_mask & (date_period != periode_clean)
    reasons.loc[is_period_mismatch & reasons.isna()] = "DATE_PERIOD_MISMATCH"

    # Route rows: rows without a reason code are valid
    valid_mask = reasons.isna()

    valid_df = df.loc[valid_mask].copy().reset_index(drop=True)

    quarantined_df = df.loc[~valid_mask].copy()
    quarantined_df["quarantine_reason"] = reasons.loc[~valid_mask].values
    quarantined_df = quarantined_df.reset_index(drop=True)

    return ValidationResult(valid=valid_df, quarantined=quarantined_df)
