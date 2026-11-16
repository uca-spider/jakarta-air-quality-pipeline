"""Unit and integration tests for layout auto-detector."""

import io
from pathlib import Path
import pytest
from src.ingestion.models import LayoutType, LayoutMismatchError
from src.ingestion.detector import (
    detect_layout,
    read_and_detect,
    EXPECTED_LAYOUT_COLUMNS,
)


def _make_html_table(columns: list[str]) -> str:
    headers = "".join(f"<th>{col}</th>" for col in columns)
    cells = "".join(f"<td>val_{col}</td>" for col in columns)
    return f"""
    <table>
      <thead><tr>{headers}</tr></thead>
      <tbody><tr>{cells}</tr></tbody>
    </table>
    """


def test_detect_layout_all_known_variants():
    """Verify that each registered layout signature is correctly identified."""
    for layout_type, expected_cols in EXPECTED_LAYOUT_COLUMNS.items():
        detected = detect_layout(expected_cols)
        assert detected == layout_type


def test_detect_layout_normalizes_casing_and_whitespace():
    """Verify column detection handles uppercase and extra whitespace gracefully."""
    cols = [
        "  Periode_Data  ",
        "Tanggal",
        "STASIUN",
        "pm10",
        "so2",
        "co",
        "o3",
        "no2",
        "MAX",
        "critical ",
        "  categori",
    ]
    assert detect_layout(cols) == LayoutType.LAYOUT_A


def test_detect_layout_rejects_unknown_columns():
    """Verify that unknown layouts raise LayoutMismatchError (fail-fast rule)."""
    unknown_cols = ["date", "station", "aqi_value"]
    with pytest.raises(LayoutMismatchError) as exc_info:
        detect_layout(unknown_cols)
    assert "Unknown layout" in str(exc_info.value)


@pytest.mark.parametrize(
    "layout_type",
    [
        LayoutType.LAYOUT_A,
        LayoutType.LAYOUT_A_PM25,
        LayoutType.LAYOUT_B_NO_PM25,
        LayoutType.LAYOUT_B,
        LayoutType.LAYOUT_C,
        LayoutType.LAYOUT_C_BULAN,
    ],
)
def test_read_and_detect_synthetic_fixtures(layout_type: LayoutType):
    """Test reading synthetic HTML tables for each layout type."""
    cols = EXPECTED_LAYOUT_COLUMNS[layout_type]
    html_source = io.StringIO(_make_html_table(cols))

    detected_type, df = read_and_detect(html_source)

    assert detected_type == layout_type
    assert list(df.columns) == cols
    assert len(df) == 1
    # Check that raw strings are preserved
    assert df.iloc[0][cols[0]] == f"val_{cols[0]}"


def test_read_and_detect_empty_or_invalid_html():
    """Test that invalid HTML without tables raises LayoutMismatchError."""
    with pytest.raises(LayoutMismatchError) as exc_info:
        read_and_detect(io.StringIO("<p>Not a table</p>"))
    assert "No table found" in str(exc_info.value)


def test_read_and_detect_on_actual_data_files():
    """Integration test against actual files present in data/raw."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw not found")

    file_to_expected_layout = {
        "stasiun-pemantau-kualitas-udara-(-spku)-tahun-2017-komponen-data.xls": LayoutType.LAYOUT_A,
        "indeks-standar-pencemaran-udara-(ispu)-tahun-2016-komponen-data.xls": LayoutType.LAYOUT_A,
        "data-indeks-standar-pencemaran-udara-di-spku-dki-jakarta-tahun-2018-komponen-data.xls": LayoutType.LAYOUT_A,
        "stasiun-pemantau-kualitas-udara-(-spku)-tahun-2020-komponen-data.xls": LayoutType.LAYOUT_A,
        "indeks-standar-pencemaran-udara-(ispu)-tahun-2021-komponen-data.xls": LayoutType.LAYOUT_A_PM25,
        "indeks-standar-pencemaran-udara-(ispu)-tahun-2019-komponen-data.xls": LayoutType.LAYOUT_B_NO_PM25,
        "indeks-standar-pencemaran-udara-(ispu)-tahun-2022-komponen-data.xls": LayoutType.LAYOUT_B,
        "data-indeks-standar-pencemar-udara-(ispu)-di-provinsi-dki-jakarta-2023-komponen-data.xls": LayoutType.LAYOUT_C,
        "data-indeks-standar-pencemar-udara-(ispu)-di-provinsi-dki-jakarta-komponen-data.xls": LayoutType.LAYOUT_C_BULAN,
    }

    for filename, expected_layout in file_to_expected_layout.items():
        file_path = raw_dir / filename
        if file_path.exists():
            layout, df = read_and_detect(file_path)
            assert layout == expected_layout
            assert len(df) > 0
