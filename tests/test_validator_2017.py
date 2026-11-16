"""Unit tests for ISPU 2017 validator and quarantine logic."""

import pandas as pd
from src.ingestion.validator_2017 import validate_ispu_2017
from src.ingestion.reader_2017 import EXPECTED_COLUMNS_2017


def make_sample_df(rows: list[list[str]]) -> pd.DataFrame:
    """Helper to construct a DataFrame with 2017 columns and string dtype."""
    return pd.DataFrame(rows, columns=EXPECTED_COLUMNS_2017, dtype=str)


def test_validate_clean_rows():
    rows = [
        [
            "201701",
            "2017-01-01",
            "DKI1 (BUNDERAN HI)",
            "49",
            "---",
            "23",
            "41",
            "3",
            "49",
            "PM10",
            "BAIK",
        ],
        [
            "201701",
            "2017-01-02",
            "DKI5 (KEBON JERUK)",
            "25",
            "10",
            "15",
            "30",
            "5",
            "30",
            "O3",
            "BAIK",
        ],
    ]
    df = make_sample_df(rows)
    result = validate_ispu_2017(df)

    assert len(result.valid) == 2
    assert len(result.quarantined) == 0
    # Ensure raw tokens are preserved
    assert result.valid.loc[0, "so2"] == "---"


def test_quarantine_shifted_station_numeric():
    # Synthetic representation of the March 2020 shifted column failure mode
    rows = [
        [
            "202003",
            "2020-03-19",
            "73",
            "22",
            "27",
            "37",
            "9",
            "73",
            "1",
            "PM10",
            "SEDANG",
        ]
    ]
    df = make_sample_df(rows)
    result = validate_ispu_2017(df)

    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_STATION_CODE"
    )
    assert result.quarantined.iloc[0]["stasiun"] == "73"


def test_quarantine_station_code_outside_1_to_5():
    rows = [
        [
            "201701",
            "2017-01-01",
            "DKI99 (UNKNOWN)",
            "49",
            "10",
            "23",
            "41",
            "3",
            "49",
            "PM10",
            "BAIK",
        ]
    ]
    df = make_sample_df(rows)
    result = validate_ispu_2017(df)

    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_STATION_CODE"
    )


def test_quarantine_missing_or_empty_station():
    rows = [
        [
            "201701",
            "2017-01-01",
            "   ",
            "49",
            "10",
            "23",
            "41",
            "3",
            "49",
            "PM10",
            "BAIK",
        ]
    ]
    df = make_sample_df(rows)
    result = validate_ispu_2017(df)

    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "MISSING_OR_EMPTY_STATION"
    )


def test_quarantine_invalid_date_format():
    # 2017 is not a leap year, 2017-02-29 is invalid; 2017-02-31 is invalid calendar date
    rows = [
        [
            "201702",
            "2017-02-29",
            "DKI1 (BUNDERAN HI)",
            "49",
            "10",
            "23",
            "41",
            "3",
            "49",
            "PM10",
            "BAIK",
        ]
    ]
    df = make_sample_df(rows)
    result = validate_ispu_2017(df)

    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_DATE_FORMAT"
    )


def test_quarantine_date_period_mismatch():
    # Date is 2017-02-01 (Feb 2017) but periode_data indicates 201701 (Jan 2017)
    rows = [
        [
            "201701",
            "2017-02-01",
            "DKI1 (BUNDERAN HI)",
            "49",
            "10",
            "23",
            "41",
            "3",
            "49",
            "PM10",
            "BAIK",
        ]
    ]
    df = make_sample_df(rows)
    result = validate_ispu_2017(df)

    assert len(result.valid) == 0
    assert len(result.quarantined) == 1
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "DATE_PERIOD_MISMATCH"
    )
