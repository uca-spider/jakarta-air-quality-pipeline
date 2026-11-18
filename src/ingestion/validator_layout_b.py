"""Validator module for Jakarta ISPU Layout B (covering 2019 and 2022)."""

import re
import pandas as pd
from src.ingestion.models import ValidationResult

# Regex matching station prefix DKI1 through DKI5 followed by word boundary
STATION_PATTERN = re.compile(r"^DKI[1-5]\b")


def validate_layout_b(df: pd.DataFrame) -> ValidationResult:
    """Validates raw Layout B ISPU DataFrame and segregates rows into valid and quarantined.

    In Layout B (2019 and 2022), the station column is 'lokasi_spku' at the end of the table.
    Date values may be in standard ISO, slash format, or Excel floating-point serial numbers
    (such as '44926.625' for 31 Dec 2022).

    Validation rules applied (in order of priority):
    1. MISSING_OR_EMPTY_STATION: Station is empty string or only whitespace.
    2. INVALID_STATION_CODE: Station does not start with DKI1 through DKI5
       (catches invalid station codes like '0' in May 2022).
    3. INVALID_DATE_FORMAT: Date cannot be parsed as ISO, DD/MM/YYYY, or Excel serial.
    4. DATE_PERIOD_MISMATCH: The YYYYMM of the parsed date does not match periode_data
       (catches February 2022 rows dated 2020-02-xx).
    5. NON_NUMERIC_MAX_VALUE: The max index value is not a numeric integer string.

    For rows that pass validation, the 'tanggal' column is standardized to ISO 'YYYY-MM-DD'.
    For quarantined rows, original tokens are preserved with an added 'quarantine_reason'.

    Args:
        df: Raw DataFrame containing Layout B columns as strings.

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

    # Station column in Layout B is lokasi_spku (fallback to stasiun if ever present)
    station_col = "lokasi_spku" if "lokasi_spku" in df.columns else "stasiun"
    stasiun_clean = df[station_col].fillna("").astype(str).str.strip()
    periode_clean = df["periode_data"].fillna("").astype(str).str.strip()
    tanggal_series = df["tanggal"].fillna("").astype(str).str.strip()
    max_series = (
        df["max"].fillna("").astype(str).str.strip()
        if "max" in df.columns
        else pd.Series("", index=df.index)
    )

    # Rule 1: Missing or empty station
    is_empty_station = stasiun_clean == ""
    reasons.loc[is_empty_station] = "MISSING_OR_EMPTY_STATION"

    # Rule 2: Invalid station code (e.g. station '0')
    matches_station_code = stasiun_clean.apply(
        lambda s: bool(STATION_PATTERN.match(s))
    )
    is_invalid_station = ~is_empty_station & ~matches_station_code
    reasons.loc[is_invalid_station & reasons.isna()] = "INVALID_STATION_CODE"

    # Rule 3: Date parsing (support ISO %Y-%m-%d, slash %d/%m/%Y, and Excel float serials)
    parsed_iso = pd.to_datetime(
        tanggal_series, format="%Y-%m-%d", errors="coerce"
    )
    parsed_slash = pd.to_datetime(
        tanggal_series, format="%d/%m/%Y", errors="coerce"
    )

    # Excel serial number parsing (e.g. '44926.625' -> 2022-12-31 15:00:00)
    numeric_serials = pd.to_numeric(tanggal_series, errors="coerce")
    parsed_excel = pd.to_datetime(
        numeric_serials, unit="D", origin="1899-12-30", errors="coerce"
    )

    parsed_dates = parsed_iso.combine_first(parsed_slash).combine_first(
        parsed_excel
    )

    is_invalid_date = parsed_dates.isna()
    reasons.loc[is_invalid_date & reasons.isna()] = "INVALID_DATE_FORMAT"

    # Rule 4: Date vs periode_data mismatch (e.g. Feb 2022 dated 2020)
    valid_dates_mask = ~is_invalid_date
    date_period = parsed_dates.dt.strftime("%Y%m")
    is_period_mismatch = valid_dates_mask & (date_period != periode_clean)
    reasons.loc[is_period_mismatch & reasons.isna()] = "DATE_PERIOD_MISMATCH"

    # Rule 5: Non-numeric max value (if max column is present)
    if "max" in df.columns:
        is_numeric_max = max_series.str.match(r"^\d+$")
        reasons.loc[~is_numeric_max & reasons.isna()] = "NON_NUMERIC_MAX_VALUE"

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
