"""Unit and integration tests for Layout A + PM2.5 validator (covering 2021)."""

from pathlib import Path
import pandas as pd
import pytest
from src.ingestion.models import ValidationResult
from src.ingestion.validator_2021 import validate_layout_a_pm25


def _make_2021_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    columns = [
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
    ]
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns].astype(str)


def test_validate_layout_a_pm25_clean_row():
    """Verify that a valid 2021 row with PM2.5 passes validation."""
    df = _make_2021_df(
        [
            {
                "periode_data": "202105",
                "tanggal": "2021-05-15",
                "stasiun": "DKI1 (BUNDERAN HI)",
                "pm10": "52",
                "pm25": "70",
                "so2": "12",
                "co": "22",
                "o3": "35",
                "no2": "10",
                "max": "70",
                "critical": "PM25",
                "categori": "SEDANG",
            }
        ]
    )
    result = validate_layout_a_pm25(df)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    assert result.valid.iloc[0]["pm25"] == "70"
    assert result.valid.iloc[0]["max"] == "70"


def test_validate_layout_a_pm25_quarantines_non_numeric_max():
    """Verify that rows with non-numeric max (simulating row 1762) are quarantined."""
    df = _make_2021_df(
        [
            {
                "periode_data": "202112",
                "tanggal": "2021-12-03",
                "stasiun": "DKI1 (BUNDERAN HI)",
                "pm10": "49",
                "pm25": "31",
                "so2": "9",
                "co": "19",
                "o3": "7",
                "no2": "49",
                "max": "PM25",  # Shifted value: text instead of numeric index
                "critical": "BAIK",
                "categori": "",
            }
        ]
    )
    result = validate_layout_a_pm25(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "NON_NUMERIC_MAX_VALUE"
    )
    assert result.quarantined.iloc[0]["max"] == "PM25"


def test_validate_layout_a_pm25_quarantines_invalid_station():
    """Verify that rows with invalid station codes are quarantined."""
    df = _make_2021_df(
        [
            {
                "periode_data": "202101",
                "tanggal": "2021-01-01",
                "stasiun": "UNKNOWN_STATION",
                "max": "50",
            }
        ]
    )
    result = validate_layout_a_pm25(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_STATION_CODE"
    )


def test_validate_layout_a_pm25_quarantines_period_mismatch():
    """Verify that date period mismatches are quarantined."""
    df = _make_2021_df(
        [
            {
                "periode_data": "202101",
                "tanggal": "2021-02-01",
                "stasiun": "DKI1 (BUNDERAN HI)",
                "max": "50",
            }
        ]
    )
    result = validate_layout_a_pm25(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "DATE_PERIOD_MISMATCH"
    )


def test_validate_layout_a_pm25_preserves_raw_tokens():
    """Verify that raw missing markers in pm25 and other pollutants are preserved."""
    df = _make_2021_df(
        [
            {
                "periode_data": "202103",
                "tanggal": "2021-03-01",
                "stasiun": "DKI3 (JAGAKARSA)",
                "pm10": "45",
                "pm25": "",  # Empty string in raw
                "so2": "---",  # Dash token in raw
                "max": "45",
                "critical": "PM10",
                "categori": "BAIK",
            }
        ]
    )
    result = validate_layout_a_pm25(df)
    assert len(result.valid) == 1
    assert result.valid.iloc[0]["pm25"] == ""
    assert result.valid.iloc[0]["so2"] == "---"


def test_validate_layout_a_pm25_on_actual_2021_file():
    """Integration test validating actual 2021 file in data/raw."""
    raw_dir = Path("data/raw")
    file_2021 = (
        raw_dir
        / "indeks-standar-pencemaran-udara-(ispu)-tahun-2021-komponen-data.xls"
    )
    if not file_2021.exists():
        pytest.skip("2021 data file not found")

    from src.ingestion.detector import read_and_detect

    _, df = read_and_detect(file_2021)
    assert len(df) == 1825

    result = validate_layout_a_pm25(df)

    # 1,824 rows must be valid, exactly 1 row (row 1762) must be quarantined
    assert len(result.valid) == 1824
    assert len(result.quarantined) == 1

    quarantined_row = result.quarantined.iloc[0]
    assert quarantined_row["tanggal"] == "2021-12-03"
    assert quarantined_row["stasiun"] == "DKI1 (BUNDERAN HI)"
    assert quarantined_row["max"] == "PM25"
    assert quarantined_row["quarantine_reason"] == "NON_NUMERIC_MAX_VALUE"
