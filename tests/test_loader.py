"""Tests for BigQuery loader (src/ingestion/loader.py).

Strategy:
- Mock google.cloud.bigquery.Client so tests run without real GCP credentials
- Verify that load_to_bigquery calls delete + insert with correct arguments
- Verify metadata columns (source_file, file_hash, loaded_at) are injected
- Verify idempotency: delete is always called before insert
- Verify handling when table does not exist yet (first-time load)
"""

import hashlib
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from google.cloud.exceptions import NotFound

from src.ingestion.models import ValidationResult, LayoutType
from src.ingestion.loader import load_to_bigquery, compute_file_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(n_valid: int = 3, n_quarantine: int = 1) -> ValidationResult:
    """Build a minimal ValidationResult with canonical columns."""
    valid_df = pd.DataFrame({
        "periode_data": ["2017-01"] * n_valid,
        "tanggal":      ["2017-01-01"] * n_valid,
        "stasiun":      ["DKI1"] * n_valid,
        "pm10":         [50.0] * n_valid,
        "pm25":         [None] * n_valid,
        "so2":          [10.0] * n_valid,
        "co":           [5.0] * n_valid,
        "o3":           [20.0] * n_valid,
        "no2":          [15.0] * n_valid,
        "max":          [50.0] * n_valid,
        "critical":     ["PM10"] * n_valid,
        "kategori":     ["BAIK"] * n_valid,
    })
    q_df = pd.DataFrame({
        "periode_data":      ["2017-01"] * n_quarantine,
        "tanggal":           ["2017-01-01"] * n_quarantine,
        "stasiun":           ["DKI1"] * n_quarantine,
        "pm10":              [50.0] * n_quarantine,
        "pm25":              [None] * n_quarantine,
        "so2":               [10.0] * n_quarantine,
        "co":                [5.0] * n_quarantine,
        "o3":                [20.0] * n_quarantine,
        "no2":               [15.0] * n_quarantine,
        "max":               [50.0] * n_quarantine,
        "critical":          ["PM10"] * n_quarantine,
        "kategori":          ["BAIK"] * n_quarantine,
        "quarantine_reason": ["INVALID_STATION_CODE"] * n_quarantine,
    })
    return ValidationResult(valid=valid_df, quarantined=q_df)


# ---------------------------------------------------------------------------
# Test: compute_file_hash
# ---------------------------------------------------------------------------

def test_compute_file_hash_returns_md5_hex(tmp_path):
    """compute_file_hash returns a 32-char hex MD5 of the file contents."""
    f = tmp_path / "sample.xls"
    f.write_bytes(b"hello world")
    result = compute_file_hash(f)
    expected = hashlib.md5(b"hello world").hexdigest()
    assert result == expected
    assert len(result) == 32


def test_compute_file_hash_is_deterministic(tmp_path):
    """Same file content always produces the same hash."""
    f = tmp_path / "sample.xls"
    f.write_bytes(b"test content")
    assert compute_file_hash(f) == compute_file_hash(f)


# ---------------------------------------------------------------------------
# Test: load_to_bigquery
# ---------------------------------------------------------------------------

@patch("src.ingestion.loader.bigquery.Client")
def test_load_injects_metadata_columns(mock_client_cls, tmp_path):
    """load_to_bigquery adds source_file, file_hash, loaded_at to valid rows."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_bytes(b"fake content")
    result = _make_result(n_valid=2, n_quarantine=0)

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.query.return_value.result.return_value = None

    load_to_bigquery(result, source_file=fake_file, project="jakarta-air-quality")

    # Capture the DataFrame passed to load_table_from_dataframe
    calls = mock_client.load_table_from_dataframe.call_args_list
    valid_call = calls[0]
    df_loaded = valid_call.args[0]

    assert "source_file" in df_loaded.columns
    assert "file_hash" in df_loaded.columns
    assert "loaded_at" in df_loaded.columns
    assert df_loaded["source_file"].iloc[0] == "ISPU_2017.xls"
    assert len(df_loaded["file_hash"].iloc[0]) == 32  # MD5 hex


@patch("src.ingestion.loader.bigquery.Client")
def test_load_calls_delete_before_insert(mock_client_cls, tmp_path):
    """load_to_bigquery deletes existing rows with same file_hash before inserting."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_bytes(b"fake content")
    result = _make_result(n_valid=2, n_quarantine=1)

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.query.return_value.result.return_value = None

    load_to_bigquery(result, source_file=fake_file, project="jakarta-air-quality")

    # query() should be called twice: DELETE for ispu + DELETE for ispu_quarantine
    assert mock_client.query.call_count == 2
    query_calls = [c.args[0] for c in mock_client.query.call_args_list]
    assert any("ispu" in q and "DELETE" in q for q in query_calls)
    assert any("ispu_quarantine" in q and "DELETE" in q for q in query_calls)


@patch("src.ingestion.loader.bigquery.Client")
def test_load_handles_table_not_found_on_first_load(mock_client_cls, tmp_path):
    """load_to_bigquery ignores NotFound on DELETE when tables do not exist yet."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_bytes(b"fake content")
    result = _make_result(n_valid=2, n_quarantine=0)

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    # Simulate NotFound error on DELETE query
    mock_client.query.side_effect = NotFound("Table not found")

    # Should not raise exception
    load_to_bigquery(result, source_file=fake_file, project="jakarta-air-quality")
    assert mock_client.load_table_from_dataframe.call_count == 1


@patch("src.ingestion.loader.bigquery.Client")
def test_load_skips_quarantine_upload_when_empty(mock_client_cls, tmp_path):
    """load_to_bigquery skips quarantine table upload when quarantined df is empty."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_bytes(b"fake content")
    result = _make_result(n_valid=3, n_quarantine=0)

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.query.return_value.result.return_value = None

    load_to_bigquery(result, source_file=fake_file, project="jakarta-air-quality")

    # Only 1 load call (valid), not 2
    assert mock_client.load_table_from_dataframe.call_count == 1


@patch("src.ingestion.loader.bigquery.Client")
def test_load_uploads_to_correct_tables(mock_client_cls, tmp_path):
    """load_to_bigquery targets aq_raw.ispu and aq_raw.ispu_quarantine."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_bytes(b"fake content")
    result = _make_result(n_valid=2, n_quarantine=1)

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.query.return_value.result.return_value = None

    load_to_bigquery(result, source_file=fake_file, project="jakarta-air-quality")

    table_refs = [
        c.args[1] for c in mock_client.load_table_from_dataframe.call_args_list
    ]
    assert any("ispu" in str(t) for t in table_refs)
    assert any("ispu_quarantine" in str(t) for t in table_refs)
