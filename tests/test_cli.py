"""Tests for CLI runner (src/ingestion/cli.py).

Strategy:
- Mock dispatch_and_validate so tests don't touch real files
- Capture stdout to assert printed output
"""

import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ingestion.models import ValidationResult, LayoutType
from src.ingestion.cli import process_file, process_dir


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

    with patch("src.ingestion.cli.dispatch_and_validate", return_value=mock_result) as mock_dispatch:
        # Patch layout detection (returned as attribute on result by dispatcher)
        # We pass layout_type back via the mock's side effect on result
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
