"""Cross-row validation rules that need to see the whole file, not one row at a time."""

import pandas as pd

from src.ingestion.models import ValidationResult

DUPLICATE_KEY_REASON = "DUPLICATE_DATE_STATION_IN_FILE"

# Same station-code extraction as dbt staging (stg_ispu), so both layers agree on the key.
_STATION_CODE = r"^(DKI[1-5])"


def quarantine_duplicate_keys(result: ValidationResult) -> ValidationResult:
    """Quarantine every valid row whose (tanggal, station) key occurs more than once in the file.

    Background: some source files repeat a date whose day equals its month (for example
    2016-11-11 or 2020-06-06) across rows holding different values. The date is valid per
    row and matches ``periode_data``, so row-level validators accept it. Which of the rows
    is the real one cannot be determined from the file, so keeping any of them would be
    guessing. The whole group is quarantined instead.

    Must run after the layout validators (``tanggal`` is ISO ``YYYY-MM-DD`` by then) and
    before harmonization (layout B still names the station column ``lokasi_spku``).
    """
    valid = result.valid
    if valid.empty:
        return result

    station_col = "lokasi_spku" if "lokasi_spku" in valid.columns else "stasiun"
    station_code = (
        valid[station_col]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .str.extract(_STATION_CODE, expand=False)
    )
    key = pd.DataFrame({"tanggal": valid["tanggal"], "station": station_code})
    is_duplicate = key.duplicated(keep=False)
    if not is_duplicate.any():
        return result

    moved = valid.loc[is_duplicate].copy()
    moved["quarantine_reason"] = DUPLICATE_KEY_REASON

    quarantined = (
        moved.reset_index(drop=True)
        if result.quarantined.empty
        else pd.concat([result.quarantined, moved], ignore_index=True)
    )
    return ValidationResult(
        valid=valid.loc[~is_duplicate].reset_index(drop=True),
        quarantined=quarantined,
    )
