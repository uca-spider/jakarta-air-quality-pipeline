"""Tests for CLI runner (src/ingestion/cli.py).

Strategy:
- Mock dispatch_and_validate so tests don't touch real files
- Mock load_to_bigquery so tests don't touch BigQuery
- Mock upload_file_to_gcs so tests don't touch Google Cloud Storage
- Capture stdout to assert printed output
"""

import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ingestion.models import ValidationResult, LayoutType
from src.ingestion.cli import process_file, process_dir, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(layout: LayoutType, n_valid: int, n_quarantine: int) -> ValidationResult:
    """Build a fake ValidationResult with the given row counts."""
    valid_df = pd.DataFrame({"tanggal": range(n_valid)})
    q_df = pd.DataFrame({"tanggal": range(n_quarantine)})
    return ValidationResult(valid=valid_df, quarantined=q_df)


# ---------------------------------------------------------------------------
# Test: process_file
# ---------------------------------------------------------------------------

def test_process_single_file_prints_summary(capsys, tmp_path):
    """process_file prints layout, valid count, and quarantine count."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_text("<table></table>")  # file harus ada di disk

    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=1825, n_quarantine=0)

    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result):
        process_file(fake_file)

    captured = capsys.readouterr()
    assert "ISPU_2017.xls" in captured.out
    assert "1825" in captured.out
    assert "0" in captured.out


def test_process_file_not_found_prints_error(capsys, tmp_path):
    """process_file prints an error message if the file does not exist."""
    missing = tmp_path / "ghost.xls"
    process_file(missing)

    captured = capsys.readouterr()
    assert "not found" in captured.out.lower() or "error" in captured.out.lower()


def test_process_file_layout_mismatch_prints_error(capsys, tmp_path):
    """process_file prints an error message on LayoutMismatchError."""
    from src.ingestion.models import LayoutMismatchError

    fake_file = tmp_path / "weird.xls"
    fake_file.write_text("<table></table>")

    with patch("src.ingestion.cli.dispatch_and_validate", side_effect=LayoutMismatchError("unknown")):
        process_file(fake_file)

    captured = capsys.readouterr()
    assert "error" in captured.out.lower() or "mismatch" in captured.out.lower()


def test_process_file_with_load_calls_loader(capsys, tmp_path):
    """process_file calls load_to_bigquery when load=True and project is provided."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_text("<table></table>")

    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=10, n_quarantine=0)

    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.load_to_bigquery") as mock_loader:
        process_file(fake_file, load=True, project="test-project")

    mock_loader.assert_called_once_with(mock_result, source_file=fake_file, project="test-project")
    captured = capsys.readouterr()
    assert "Loaded to BigQuery" in captured.out or "BigQuery" in captured.out


def test_process_file_with_bucket_uploads_to_gcs(capsys, tmp_path):
    """process_file calls upload_file_to_gcs when load=True and bucket is provided."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_text("<table></table>")

    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=10, n_quarantine=0)

    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.load_to_bigquery"), \
         patch("src.ingestion.cli.upload_file_to_gcs", return_value="gs://hudza-aq-raw/raw/ISPU_2017.xls") as mock_gcs:
        process_file(fake_file, load=True, project="test-project", bucket="hudza-aq-raw")

    mock_gcs.assert_called_once_with(fake_file, bucket_name="hudza-aq-raw", project="test-project")
    captured = capsys.readouterr()
    assert "Uploaded raw file to gs://hudza-aq-raw/raw/ISPU_2017.xls" in captured.out


def test_process_file_without_load_does_not_call_loader(capsys, tmp_path):
    """process_file does not call load_to_bigquery when load=False."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_text("<table></table>")

    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=10, n_quarantine=0)

    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.load_to_bigquery") as mock_loader:
        process_file(fake_file, load=False)

    mock_loader.assert_not_called()


# ---------------------------------------------------------------------------
# Test: process_dir
# ---------------------------------------------------------------------------

def test_process_dir_processes_all_xls_files(capsys, tmp_path):
    """process_dir iterates over all .xls/.html files in a directory."""
    (tmp_path / "file_a.xls").write_text("<table></table>")
    (tmp_path / "file_b.xls").write_text("<table></table>")
    (tmp_path / "readme.txt").write_text("ignore me")  # non-HTML, should be skipped

    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=10, n_quarantine=0)

    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result):
        process_dir(tmp_path)

    captured = capsys.readouterr()
    assert "file_a.xls" in captured.out
    assert "file_b.xls" in captured.out
    assert "readme.txt" not in captured.out


def test_process_dir_passes_load_flags(capsys, tmp_path):
    """process_dir passes load and project down to process_file."""
    (tmp_path / "file_a.xls").write_text("<table></table>")
    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=10, n_quarantine=0)

    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.load_to_bigquery") as mock_loader:
        process_dir(tmp_path, load=True, project="test-project")

    assert mock_loader.call_count == 1


# ---------------------------------------------------------------------------
# Test: main entrypoint
# ---------------------------------------------------------------------------

def test_main_with_load_and_project(tmp_path):
    """main parses --load and --project and invokes process_file."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_text("<table></table>")

    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=5, n_quarantine=0)

    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.load_to_bigquery") as mock_loader:
        main(["--file", str(fake_file), "--load", "--project", "test-project"])

    mock_loader.assert_called_once_with(mock_result, source_file=fake_file, project="test-project")


def test_main_load_without_project_prints_error(capsys, tmp_path, monkeypatch):
    """main prints an error when --load is passed without --project and without GCP_PROJECT env."""
    fake_file = tmp_path / "ISPU_2017.xls"
    fake_file.write_text("<table></table>")
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    with pytest.raises(SystemExit):
        main(["--file", str(fake_file), "--load"])

    captured = capsys.readouterr()
    assert "--project" in captured.err or "--project" in captured.out


# ---------------------------------------------------------------------------
# Test: failures are reported (exit code / return values)
# ---------------------------------------------------------------------------

def test_process_file_returns_true_on_success(tmp_path):
    f = tmp_path / "ok.xls"
    f.write_text("<table></table>")
    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=3, n_quarantine=0)
    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result):
        assert process_file(f) is True


def test_process_file_returns_false_when_bigquery_load_fails(capsys, tmp_path):
    f = tmp_path / "bad.xls"
    f.write_text("<table></table>")
    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=3, n_quarantine=0)
    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.load_to_bigquery", side_effect=RuntimeError("no credentials")):
        assert process_file(f, load=True, project="p") is False


def test_process_file_returns_false_when_gcs_upload_fails(tmp_path):
    f = tmp_path / "bad.xls"
    f.write_text("<table></table>")
    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=3, n_quarantine=0)
    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.upload_file_to_gcs", side_effect=RuntimeError("denied")), \
         patch("src.ingestion.cli.load_to_bigquery"):
        assert process_file(f, load=True, project="p", bucket="b") is False


def test_process_file_returns_false_when_file_missing(tmp_path):
    assert process_file(tmp_path / "missing.xls") is False


def test_process_dir_reports_failed_count(capsys, tmp_path):
    (tmp_path / "a.xls").write_text("<table></table>")
    (tmp_path / "b.xls").write_text("<table></table>")
    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=3, n_quarantine=0)
    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.load_to_bigquery", side_effect=RuntimeError("boom")):
        failed = process_dir(tmp_path, load=True, project="p")
    assert failed == 2
    assert "2 failed" in capsys.readouterr().out


def test_main_exits_one_when_any_file_fails(tmp_path):
    (tmp_path / "a.xls").write_text("<table></table>")
    mock_result = _make_result(LayoutType.LAYOUT_A, n_valid=3, n_quarantine=0)
    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result), \
         patch("src.ingestion.cli.load_to_bigquery", side_effect=RuntimeError("boom")):
        with pytest.raises(SystemExit) as exc:
            main(["--dir", str(tmp_path), "--load", "--project", "p"])
    assert exc.value.code == 1
