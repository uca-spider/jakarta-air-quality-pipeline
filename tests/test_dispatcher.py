"""Unit tests for ISPU ingestion dispatcher."""

import io
import pytest
from src.ingestion.models import LayoutMismatchError, ValidationResult
from src.ingestion.detector import EXPECTED_LAYOUT_COLUMNS
from src.ingestion.models import LayoutType
from src.ingestion.dispatcher import dispatch_and_validate


def _make_html_table(columns: list[str], row_data: list[str]) -> str:
    headers = "".join(f"<th>{col}</th>" for col in columns)
    cells = "".join(f"<td>{val}</td>" for val in row_data)
    return f"""
    <table>
      <thead><tr>{headers}</tr></thead>
      <tbody><tr>{cells}</tr></tbody>
    </table>
    """


def test_dispatch_and_validate_routes_layout_a_correctly():
    """Verify that Layout A sources are dispatched to Layout A validator."""
    cols = EXPECTED_LAYOUT_COLUMNS[LayoutType.LAYOUT_A]
    # Synthetic valid row for 2017 Layout A
    row = [
        "201701",
        "2017-01-01",
        "DKI1 (BUNDERAN HI)",
        "40",
        "---",
        "15",
        "30",
        "5",
        "40",
        "PM10",
        "BAIK",
    ]
    html = io.StringIO(_make_html_table(cols, row))

    result = dispatch_and_validate(html)

    assert isinstance(result, ValidationResult)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 0
    assert result.valid.iloc[0]["stasiun"] == "DKI1 (BUNDERAN HI)"


def test_dispatch_and_validate_rejects_unknown_layout():
    """Verify that unknown layouts fail fast."""
    html = io.StringIO("<table><tr><th>col1</th><th>col2</th></tr></table>")
    with pytest.raises(LayoutMismatchError):
        dispatch_and_validate(html)


def test_dispatch_and_validate_unimplemented_layout_raises_not_implemented():
    """Verify that layouts awaiting validator implementation raise informative NotImplementedError."""
    cols = EXPECTED_LAYOUT_COLUMNS[LayoutType.LAYOUT_C]
    html = io.StringIO(_make_html_table(cols, ["val"] * len(cols)))

    with pytest.raises(NotImplementedError) as exc_info:
        dispatch_and_validate(html)
    assert "Validator for layout_c is not yet implemented" in str(exc_info.value)
