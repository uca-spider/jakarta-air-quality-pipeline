"""Tests for the cross-row duplicate-key rule (same date + station within one file)."""

import io

import pandas as pd

from src.ingestion.cross_row import (
    DUPLICATE_KEY_REASON,
    quarantine_duplicate_keys,
)
from src.ingestion.detector import EXPECTED_LAYOUT_COLUMNS
from src.ingestion.dispatcher import dispatch_and_validate
from src.ingestion.models import LayoutType, ValidationResult


def _result(rows: list[dict], station_col: str = "stasiun") -> ValidationResult:
    valid = pd.DataFrame(rows).rename(columns={"stasiun": station_col})
    quarantined = pd.DataFrame(
        {"tanggal": pd.Series(dtype=str), "quarantine_reason": pd.Series(dtype=str)}
    )
    return ValidationResult(valid=valid, quarantined=quarantined)


def _row(date: str, station: str, max_value: str) -> dict:
    return {"tanggal": date, "stasiun": station, "max": max_value}


def test_unique_keys_are_untouched():
    res = _result([_row("2016-10-09", "DKI1 (HI)", "40"), _row("2016-10-10", "DKI1 (HI)", "41")])
    out = quarantine_duplicate_keys(res)
    assert len(out.valid) == 2
    assert out.quarantined.empty


def test_every_row_of_a_duplicate_group_is_quarantined():
    """No row of an ambiguous group is kept: choosing one would be guessing."""
    res = _result(
        [
            _row("2016-11-11", "DKI1 (HI)", "40"),
            _row("2016-11-11", "DKI1 (HI)", "55"),
            _row("2016-11-11", "DKI1 (HI)", "70"),
            _row("2016-11-12", "DKI1 (HI)", "41"),
        ]
    )
    out = quarantine_duplicate_keys(res)
    assert list(out.valid["tanggal"]) == ["2016-11-12"]
    assert len(out.quarantined) == 3
    assert set(out.quarantined["quarantine_reason"]) == {DUPLICATE_KEY_REASON}


def test_station_label_variants_collapse_to_one_key():
    """'DKI1 (BUNDERAN HI)' and 'DKI1' are the same station, matching the dbt key."""
    res = _result([_row("2020-06-06", "DKI1 (BUNDERAN HI)", "40"), _row("2020-06-06", "dki1", "50")])
    out = quarantine_duplicate_keys(res)
    assert out.valid.empty
    assert len(out.quarantined) == 2


def test_different_stations_same_date_are_not_duplicates():
    res = _result([_row("2016-10-10", "DKI1 (HI)", "40"), _row("2016-10-10", "DKI2 (KG)", "41")])
    out = quarantine_duplicate_keys(res)
    assert len(out.valid) == 2


def test_layout_b_station_column_lokasi_spku_is_supported():
    res = _result(
        [_row("2019-01-01", "DKI4", "40"), _row("2019-01-01", "DKI4", "41")],
        station_col="lokasi_spku",
    )
    out = quarantine_duplicate_keys(res)
    assert out.valid.empty
    assert len(out.quarantined) == 2


def test_existing_quarantine_rows_are_preserved():
    res = _result([_row("2016-11-11", "DKI1", "40"), _row("2016-11-11", "DKI1", "41")])
    existing = pd.DataFrame(
        {"tanggal": ["2016-09-01"], "quarantine_reason": ["DATE_PERIOD_MISMATCH"]}
    )
    out = quarantine_duplicate_keys(ValidationResult(valid=res.valid, quarantined=existing))
    assert len(out.quarantined) == 3
    assert "DATE_PERIOD_MISMATCH" in set(out.quarantined["quarantine_reason"])


def test_empty_valid_frame_is_returned_unchanged():
    res = ValidationResult(
        valid=pd.DataFrame(columns=["tanggal", "stasiun"]),
        quarantined=pd.DataFrame(columns=["tanggal", "quarantine_reason"]),
    )
    out = quarantine_duplicate_keys(res)
    assert out.valid.empty and out.quarantined.empty


def _html(columns: list[str], rows: list[list[str]]) -> io.StringIO:
    headers = "".join(f"<th>{c}</th>" for c in columns)
    body = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in rows)
    return io.StringIO(f"<table><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table>")


def test_dispatcher_applies_rule_end_to_end_for_layout_a():
    """Regression for the source defect: dates whose day equals the month (e.g. 2016-11-11)
    repeat with different values and must not reach the valid table."""
    cols = EXPECTED_LAYOUT_COLUMNS[LayoutType.LAYOUT_A]

    def row(date: str, value: str) -> list[str]:
        return ["201611", date, "DKI1 (BUNDERAN HI)", value, "---", "15", "30", "5", value, "PM10", "BAIK"]

    rows = [row("2016-11-10", "40"), row("2016-11-11", "41"), row("2016-11-11", "55")]
    result = dispatch_and_validate(_html(cols, rows))

    assert list(result.valid["tanggal"]) == ["2016-11-10"]
    assert len(result.quarantined) == 2
    assert set(result.quarantined["quarantine_reason"]) == {DUPLICATE_KEY_REASON}
