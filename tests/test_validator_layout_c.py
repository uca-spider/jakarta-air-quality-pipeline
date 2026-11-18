"""Unit and integration tests for Layout C validator (covering 2023 and 2024-2025)."""

from pathlib import Path
import pandas as pd
import pytest
from src.ingestion.models import ValidationResult
from src.ingestion.validator_layout_c import validate_layout_c


def _make_layout_c_df(
    rows: list[dict[str, str]], with_bulan: bool = False
) -> pd.DataFrame:
    if with_bulan:
        columns = [
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
        ]
    else:
        columns = [
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
        ]
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns].astype(str)


def test_validate_layout_c_clean_row_2023():
    """Verify that a standard 2023 row with Indonesian column names and ISO date passes."""
    df = _make_layout_c_df(
        [
            {
                "periode_data": "202305",
                "tanggal": "2023-05-15",
                "stasiun": "DKI1 BUNDERAN HI",
                "pm_sepuluh": "45",
                "pm_duakomalima": "60",
                "sulfur_dioksida": "20",
                "karbon_monoksida": "10",
                "ozon": "30",
                "nitrogen_dioksida": "15",
                "max": "60",
                "parameter_pencemar_kritis": "PM25",
                "kategori": "SEDANG",
            }
        ],
        with_bulan=False,
    )
    result = validate_layout_c(df)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    assert result.valid.iloc[0]["tanggal"] == "2023-05-15"
    assert result.valid.iloc[0]["stasiun"] == "DKI1 BUNDERAN HI"


def test_validate_layout_c_bulan_synthesizes_date():
    """Verify that day-of-month string in Layout C+Bulan is synthesized to ISO YYYY-MM-DD."""
    df = _make_layout_c_df(
        [
            {
                "periode_data": "202401",
                "bulan": "1",
                "tanggal": "21",  # Day of month only
                "stasiun": "DKI3 JAGAKARSA",
                "max": "79",
                "kategori": "SEDANG",
            }
        ],
        with_bulan=True,
    )
    result = validate_layout_c(df)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    # Synthesized to full ISO YYYY-MM-DD
    assert result.valid.iloc[0]["tanggal"] == "2024-01-21"


def test_validate_layout_c_quarantines_impossible_calendar_date():
    """Verify that impossible dates (e.g. 31 September 2025 in row 3195) are quarantined."""
    df = _make_layout_c_df(
        [
            {
                "periode_data": "202509",
                "bulan": "9",
                "tanggal": "31",  # 31 Sept does not exist
                "stasiun": "DKI5 KEBON JERUK",
                "max": "N/A",
                "kategori": "N/A",
            }
        ],
        with_bulan=True,
    )
    result = validate_layout_c(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_DATE_FORMAT"
    )
    assert result.quarantined.iloc[0]["tanggal"] == "31"


def test_validate_layout_c_handles_tidak_ada_data_missing_tokens():
    """Verify that rows with category 'TIDAK ADA DATA' and tokens like 'N/A' or '-' pass."""
    df = _make_layout_c_df(
        [
            {
                "periode_data": "202403",
                "bulan": "3",
                "tanggal": "22",
                "stasiun": "DKI4 LUBANG BUAYA",
                "pm_sepuluh": "N/A",
                "pm_duakomalima": "N/A",
                "max": "N/A",
                "parameter_pencemar_kritis": "N/A",
                "kategori": "TIDAK ADA DATA",
            }
        ],
        with_bulan=True,
    )
    result = validate_layout_c(df)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    assert result.valid.iloc[0]["tanggal"] == "2024-03-22"
    assert result.valid.iloc[0]["max"] == "N/A"


def test_validate_layout_c_quarantines_invalid_station():
    """Verify that rows with invalid station prefix are quarantined."""
    df = _make_layout_c_df(
        [
            {
                "periode_data": "202301",
                "tanggal": "2023-01-01",
                "stasiun": "INVALID_STATION_NAME",
                "max": "50",
            }
        ],
        with_bulan=False,
    )
    result = validate_layout_c(df)
    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_STATION_CODE"
    )


def test_validate_layout_c_on_actual_files():
    """Integration test validating actual 2023 and 2024-2025 files in data/raw."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw not found")

    from src.ingestion.detector import read_and_detect

    # 1. Test 2023: all 1,825 rows must be valid
    file_2023 = (
        raw_dir
        / "data-indeks-standar-pencemar-udara-(ispu)-di-provinsi-dki-jakarta-2023-komponen-data.xls"
    )
    if file_2023.exists():
        _, df_2023 = read_and_detect(file_2023)
        assert len(df_2023) == 1825
        res_2023 = validate_layout_c(df_2023)
        assert len(res_2023.valid) == 1825
        assert len(res_2023.quarantined) == 0

    # 2. Test 2024-2025: 3,501 rows total -> 3,500 valid, exactly 1 row (31 Sept) quarantined
    file_2024 = (
        raw_dir
        / "data-indeks-standar-pencemar-udara-(ispu)-di-provinsi-dki-jakarta-komponen-data.xls"
    )
    if file_2024.exists():
        _, df_2024 = read_and_detect(file_2024)
        assert len(df_2024) == 3501
        res_2024 = validate_layout_c(df_2024)
        assert len(res_2024.valid) == 3500
        assert len(res_2024.quarantined) == 1
        assert (
            res_2024.quarantined.iloc[0]["quarantine_reason"]
            == "INVALID_DATE_FORMAT"
        )
        assert res_2024.quarantined.iloc[0]["periode_data"] == "202509"
        assert res_2024.quarantined.iloc[0]["tanggal"] == "31"
