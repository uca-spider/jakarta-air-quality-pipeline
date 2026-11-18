"""Validator module for Jakarta ISPU Layout C (covering 2023 and 2024-2025)."""

import re
import pandas as pd
from src.ingestion.models import ValidationResult

# Regex matching station prefix DKI1 through DKI5 followed by word boundary
STATION_PATTERN = re.compile(r"^DKI[1-5]\b")

# Allowed missing markers when kategori is 'TIDAK ADA DATA'
ALLOWED_MISSING_MAX_TOKENS = {"-", "---", "N/A", "NULL", ""}


def validate_layout_c(df: pd.DataFrame) -> ValidationResult:
    """Validates raw Layout C ISPU DataFrame and segregates rows into valid and quarantined.

    Handles both:
    1. Layout C (2023): standard 12 columns with full ISO date.
    2. Layout C + Bulan (2024-2025): 13 columns where 'tanggal' contains only day-of-month (1-31).
       In this case, full calendar date is synthesized from 'periode_data' + 'tanggal'.

    Validation rules applied (in order of priority):
    1. MISSING_OR_EMPTY_STATION: Station is empty string or only whitespace.
    2. INVALID_STATION_CODE: Station does not start with DKI1 through DKI5.
    3. INVALID_DATE_FORMAT: Date cannot be parsed as valid calendar date
       (catches impossible calendar dates like 31 September 2025).
    4. DATE_PERIOD_MISMATCH: The YYYYMM of the parsed date does not match periode_data.
    5. NON_NUMERIC_MAX_VALUE: The max index value is not numeric digits (unless kategori is 'TIDAK ADA DATA').

    For rows that pass validation, the 'tanggal' column is standardized to ISO 'YYYY-MM-DD'.
    For quarantined rows, original tokens are preserved with an added 'quarantine_reason'.

    Args:
        df: Raw DataFrame containing Layout C columns as strings.

    Returns:
        ValidationResult: Dataclass containing:
            - valid: DataFrame with rows that passed all checks (dates standardized).
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
    max_series = (
        df["max"].fillna("").astype(str).str.strip()
        if "max" in df.columns
        else pd.Series("", index=df.index)
    )
    kategori_series = (
        df["kategori"].fillna("").astype(str).str.strip()
        if "kategori" in df.columns
        else pd.Series("", index=df.index)
    )

    # Rule 1: Missing or empty station
    is_empty_station = stasiun_clean == ""
    reasons.loc[is_empty_station] = "MISSING_OR_EMPTY_STATION"

    # Rule 2: Invalid station code
    matches_station_code = stasiun_clean.apply(
        lambda s: bool(STATION_PATTERN.match(s))
    )
    is_invalid_station = ~is_empty_station & ~matches_station_code
    reasons.loc[is_invalid_station & reasons.isna()] = "INVALID_STATION_CODE"

    # Rule 3: Date parsing
    # Check if tanggal consists of day-of-month digits (e.g. '1' to '31')
    is_day_only = (
        "bulan" in df.columns
        or tanggal_series.str.match(r"^\d{1,2}$").all()
    )

    if is_day_only:
        # Synthesize date from periode_data (YYYYMM) + day (DD)
        synth_dates = (
            periode_clean.str.slice(0, 4)
            + "-"
            + periode_clean.str.slice(4, 6)
            + "-"
            + tanggal_series.str.zfill(2)
        )
        parsed_dates = pd.to_datetime(
            synth_dates, format="%Y-%m-%d", errors="coerce"
        )
    else:
        parsed_iso = pd.to_datetime(
            tanggal_series, format="%Y-%m-%d", errors="coerce"
        )
        parsed_slash = pd.to_datetime(
            tanggal_series, format="%d/%m/%Y", errors="coerce"
        )
        parsed_dates = parsed_iso.combine_first(parsed_slash)

    is_invalid_date = parsed_dates.isna()
    reasons.loc[is_invalid_date & reasons.isna()] = "INVALID_DATE_FORMAT"

    # Rule 4: Date vs periode_data mismatch
    valid_dates_mask = ~is_invalid_date
    date_period = parsed_dates.dt.strftime("%Y%m")
    is_period_mismatch = valid_dates_mask & (date_period != periode_clean)
    reasons.loc[is_period_mismatch & reasons.isna()] = "DATE_PERIOD_MISMATCH"

    # Rule 5: Max value numeric check
    if "max" in df.columns:
        is_numeric = max_series.str.match(r"^\d+$")
        is_missing_token = max_series.isin(ALLOWED_MISSING_MAX_TOKENS) & (
            kategori_series == "TIDAK ADA DATA"
        )
        is_valid_max = is_numeric | is_missing_token
        reasons.loc[~is_valid_max & reasons.isna()] = "NON_NUMERIC_MAX_VALUE"

    # Route rows: rows without a reason code are valid
    valid_mask = reasons.isna()

    # Valid rows: standardize tanggal to ISO YYYY-MM-DD
    valid_df = df.loc[valid_mask].copy().reset_index(drop=True)
    valid_df["tanggal"] = (
        parsed_dates.loc[valid_mask].dt.strftime("%Y-%m-%d").values
    )

    # Quarantined rows: retain exact raw tokens plus quarantine_reason
    quarantined_df = df.loc[~valid_mask].copy()
    quarantined_df["quarantine_reason"] = reasons.loc[~valid_mask].values
    quarantined_df = quarantined_df.reset_index(drop=True)

    return ValidationResult(valid=valid_df, quarantined=quarantined_df)
