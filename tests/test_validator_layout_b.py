"""Unit and integration tests for Layout B validator (covering 2019 and 2022)."""

from pathlib import Path
import pandas as pd
import pytest
from src.ingestion.models import ValidationResult
from src.ingestion.validator_layout_b import validate_layout_b


def _make_layout_b_df(
    rows: list[dict[str, str]], with_pm25: bool = True
) -> pd.DataFrame:
    if with_pm25:
        columns = [
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
        ]
    else:
        columns = [
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
        ]
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns].astype(str)


def test_validate_layout_b_clean_row():
    """Verify that a valid Layout B row with lokasi_spku at the end passes validation."""
    df = _make_layout_b_df(
        [
            {
                "periode_data": "202207",
                "tanggal": "2022-07-06",
                "pm_10": "50",
                "pm_duakomalima": "75",
                "so2": "20",
                "co": "15",
                "o3": "30",
                "no2": "10",
                "max": "75",
                "critical": "PM25",
                "categori": "SEDANG",
                "lokasi_spku": "DKI4",
            }
        ]
    )
    result = validate_layout_b(df)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    assert result.valid.iloc[0]["lokasi_spku"] == "DKI4"
    assert result.valid.iloc[0]["tanggal"] == "2022-07-06"


def test_validate_layout_b_excel_serial_date_standardized():
    """Verify that Excel serial dates (e.g. 44926.625 for 31 Dec 2022) are parsed and standardized."""
    df = _make_layout_b_df(
        [
            {
                "periode_data": "202212",
                "tanggal": "44926.625",  # 31 Dec 2022 serial number
                "lokasi_spku": "DKI4",
                "max": "60",
            }
        ]
    )
    result = validate_layout_b(df)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    # Standardized to ISO YYYY-MM-DD
    assert result.valid.iloc[0]["tanggal"] == "2022-12-31"


def test_validate_layout_b_quarantines_station_zero():
    """Verify that rows with station '0' (as in May 2022) are quarantined."""
    df = _make_layout_b_df(
        [
            {
                "periode_data": "202205",
                "tanggal": "2022-05-31",
                "lokasi_spku": "0",  # Invalid station code
                "max": "100",
            }
        ]
    )
    result = validate_layout_b(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_STATION_CODE"
    )
    assert result.quarantined.iloc[0]["lokasi_spku"] == "0"


def test_validate_layout_b_quarantines_period_mismatch():
    """Verify that rows with mismatched date and period (e.g. Feb 2022 dated 2020) are quarantined."""
    df = _make_layout_b_df(
        [
            {
                "periode_data": "202202",
                "tanggal": "2020-02-01",  # Year 2020 inside 202202 period
                "lokasi_spku": "DKI4",
                "max": "45",
            }
        ]
    )
    result = validate_layout_b(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "DATE_PERIOD_MISMATCH"
    )


def test_validate_layout_b_handles_both_variants():
    """Verify that validate_layout_b handles both 2019 (without PM2.5) and 2022 (with PM2.5)."""
    # 2019 row (pm10, no pm_duakomalima)
    df_2019 = _make_layout_b_df(
        [
            {
                "periode_data": "201903",
                "tanggal": "2019-03-01",
                "pm10": "40",
                "lokasi_spku": "DKI3",
                "max": "40",
            }
        ],
        with_pm25=False,
    )
    res_2019 = validate_layout_b(df_2019)
    assert len(res_2019.valid) == 1

    # 2022 row (pm_10 and pm_duakomalima)
    df_2022 = _make_layout_b_df(
        [
            {
                "periode_data": "202208",
                "tanggal": "2022-08-01",
                "pm_10": "50",
                "pm_duakomalima": "70",
                "lokasi_spku": "DKI2",
                "max": "70",
            }
        ],
        with_pm25=True,
    )
    res_2022 = validate_layout_b(df_2022)
    assert len(res_2022.valid) == 1


def test_validate_layout_b_on_actual_files():
    """Integration test validating actual 2019 and 2022 files in data/raw."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw not found")

    from src.ingestion.detector import read_and_detect

    # 1. Test 2019: all 345 rows must be valid
    file_2019 = (
        raw_dir
        / "indeks-standar-pencemaran-udara-(ispu)-tahun-2019-komponen-data.xls"
    )
    if file_2019.exists():
        _, df_2019 = read_and_detect(file_2019)
        assert len(df_2019) == 345
        res_2019 = validate_layout_b(df_2019)
        assert len(res_2019.valid) == 345
        assert len(res_2019.quarantined) == 0

    # 2. Test 2022: 365 rows total -> 336 valid, 29 quarantined (1 station 0 + 28 Feb date mismatch)
    file_2022 = (
        raw_dir
        / "indeks-standar-pencemaran-udara-(ispu)-tahun-2022-komponen-data.xls"
    )
    if file_2022.exists():
        _, df_2022 = read_and_detect(file_2022)
        assert len(df_2022) == 365
        res_2022 = validate_layout_b(df_2022)
        assert len(res_2022.valid) == 336
        assert len(res_2022.quarantined) == 29
        assert (
            res_2022.quarantined["quarantine_reason"] == "INVALID_STATION_CODE"
        ).sum() == 1
        assert (
            res_2022.quarantined["quarantine_reason"] == "DATE_PERIOD_MISMATCH"
        ).sum() == 28
