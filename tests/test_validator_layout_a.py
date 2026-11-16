"""Unit and integration tests for Layout A validator (covering 2016, 2017, 2018, 2020)."""

from pathlib import Path
import pandas as pd
import pytest
from src.ingestion.models import ValidationResult
from src.ingestion.validator_layout_a import validate_layout_a


def _make_layout_a_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    columns = [
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
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns].astype(str)


def test_validate_layout_a_iso_date():
    """Verify that rows with valid ISO YYYY-MM-DD dates pass validation."""
    df = _make_layout_a_df(
        [
            {
                "periode_data": "201701",
                "tanggal": "2017-01-15",
                "stasiun": "DKI1 (BUNDERAN HI)",
                "pm10": "45",
                "so2": "10",
                "co": "20",
                "o3": "30",
                "no2": "5",
                "max": "45",
                "critical": "PM10",
                "categori": "BAIK",
            }
        ]
    )
    result = validate_layout_a(df)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    assert result.valid.iloc[0]["tanggal"] == "2017-01-15"


def test_validate_layout_a_slash_date_standardized_to_iso():
    """Verify that DD/MM/YYYY dates (as in 2016 & 2018) pass and are standardized to YYYY-MM-DD."""
    df = _make_layout_a_df(
        [
            {
                "periode_data": "201801",
                "tanggal": "25/01/2018",
                "stasiun": "DKI2 (KELAPA GADING)",
                "pm10": "55",
                "so2": "15",
                "co": "25",
                "o3": "40",
                "no2": "8",
                "max": "55",
                "critical": "PM10",
                "categori": "SEDANG",
            }
        ]
    )
    result = validate_layout_a(df)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    # Date must be standardized to ISO format in the valid output
    assert result.valid.iloc[0]["tanggal"] == "2018-01-25"


def test_validate_layout_a_quarantines_numeric_station_shifted_rows():
    """Verify that shifted rows with numeric stations (March 2020 issue) are quarantined."""
    df = _make_layout_a_df(
        [
            {
                "periode_data": "202003",
                "tanggal": "2020-03-19",
                "stasiun": "73",  # Numeric shifted station
                "pm10": "22",
                "so2": "27",
                "co": "37",
                "o3": "9",
                "no2": "73",
                "max": "1",
                "critical": "PM10",
                "categori": "SEDANG",
            }
        ]
    )
    result = validate_layout_a(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_STATION_CODE"
    )
    # Original raw tokens are preserved in quarantine
    assert result.quarantined.iloc[0]["stasiun"] == "73"


def test_validate_layout_a_quarantines_period_mismatch():
    """Verify that dates not matching periode_data are quarantined."""
    df = _make_layout_a_df(
        [
            {
                "periode_data": "201801",
                "tanggal": "2018-02-05",  # Feb date with Jan period
                "stasiun": "DKI1 (BUNDERAN HI)",
            }
        ]
    )
    result = validate_layout_a(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "DATE_PERIOD_MISMATCH"
    )


def test_validate_layout_a_preserves_raw_tokens():
    """Verify that raw missing markers like '---' are preserved as strings."""
    df = _make_layout_a_df(
        [
            {
                "periode_data": "201605",
                "tanggal": "2016-05-10",
                "stasiun": "DKI3 (JAGAKARSA)",
                "so2": "---",
                "pm10": "",
            }
        ]
    )
    result = validate_layout_a(df)
    assert len(result.valid) == 1
    assert result.valid.iloc[0]["so2"] == "---"
    assert result.valid.iloc[0]["pm10"] == ""


def test_validate_layout_a_actual_files():
    """Integration test validating actual Layout A files (2016, 2017, 2018, 2020)."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw not found")

    from src.ingestion.detector import read_and_detect

    # 1. Test 2016: 1,830 rows total (1,670 valid, 160 quarantined due to real August/Nov period mismatches)
    f_2016 = (
        raw_dir
        / "indeks-standar-pencemaran-udara-(ispu)-tahun-2016-komponen-data.xls"
    )
    if f_2016.exists():
        _, df_2016 = read_and_detect(f_2016)
        res_2016 = validate_layout_a(df_2016)
        assert len(res_2016.valid) == 1670
        assert len(res_2016.quarantined) == 160
        assert (
            res_2016.quarantined["quarantine_reason"] == "DATE_PERIOD_MISMATCH"
        ).all()

    # 2. Test 2017: 1,825 rows, all valid baseline
    f_2017 = (
        raw_dir
        / "stasiun-pemantau-kualitas-udara-(-spku)-tahun-2017-komponen-data.xls"
    )
    if f_2017.exists():
        _, df_2017 = read_and_detect(f_2017)
        res_2017 = validate_layout_a(df_2017)
        assert len(res_2017.valid) == 1825
        assert len(res_2017.quarantined) == 0

    # 3. Test 2018: 1,825 rows, all valid (slash dates successfully parsed and standardized)
    f_2018 = (
        raw_dir
        / "data-indeks-standar-pencemaran-udara-di-spku-dki-jakarta-tahun-2018-komponen-data.xls"
    )
    if f_2018.exists():
        _, df_2018 = read_and_detect(f_2018)
        res_2018 = validate_layout_a(df_2018)
        assert len(res_2018.valid) == 1825
        assert len(res_2018.quarantined) == 0

    # 4. Test 2020: 1,830 rows total (1,620 valid, 210 quarantined: 155 March shifted, 55 Nov format mismatches)
    f_2020 = (
        raw_dir
        / "stasiun-pemantau-kualitas-udara-(-spku)-tahun-2020-komponen-data.xls"
    )
    if f_2020.exists():
        _, df_2020 = read_and_detect(f_2020)
        res_2020 = validate_layout_a(df_2020)
        assert len(res_2020.valid) == 1620
        assert len(res_2020.quarantined) == 210
        assert (
            res_2020.quarantined["quarantine_reason"] == "INVALID_STATION_CODE"
        ).sum() == 155
        assert (
            res_2020.quarantined["quarantine_reason"] == "DATE_PERIOD_MISMATCH"
        ).sum() == 55
