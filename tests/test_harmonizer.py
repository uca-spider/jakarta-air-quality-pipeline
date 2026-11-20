"""Unit and integration tests for schema harmonizer."""

from pathlib import Path
import pandas as pd
import pytest
from src.ingestion.models import LayoutType
from src.ingestion.detector import EXPECTED_LAYOUT_COLUMNS
from src.ingestion.harmonizer import (
    CANONICAL_COLUMNS,
    QUARANTINE_COLUMNS,
    harmonize_layout,
)
from src.ingestion.dispatcher import dispatch_and_validate


def _make_dummy_row(layout: LayoutType) -> pd.DataFrame:
    cols = EXPECTED_LAYOUT_COLUMNS[layout]
    data = {c: [f"val_{c}"] for c in cols}
    return pd.DataFrame(data).astype(str)


def test_harmonize_layout_a():
    """Verify Layout A maps to CANONICAL_COLUMNS and inserts empty pm25."""
    df = _make_dummy_row(LayoutType.LAYOUT_A)
    harmonized = harmonize_layout(df, LayoutType.LAYOUT_A)

    assert list(harmonized.columns) == CANONICAL_COLUMNS
    assert harmonized.iloc[0]["pm25"] == ""
    assert harmonized.iloc[0]["kategori"] == "val_categori"


def test_harmonize_layout_a_pm25():
    """Verify Layout A + PM2.5 maps to CANONICAL_COLUMNS."""
    df = _make_dummy_row(LayoutType.LAYOUT_A_PM25)
    harmonized = harmonize_layout(df, LayoutType.LAYOUT_A_PM25)

    assert list(harmonized.columns) == CANONICAL_COLUMNS
    assert harmonized.iloc[0]["pm25"] == "val_pm25"
    assert harmonized.iloc[0]["kategori"] == "val_categori"


def test_harmonize_layout_b_no_pm25():
    """Verify Layout B without PM2.5 renames lokasi_spku to stasiun and adds pm25."""
    df = _make_dummy_row(LayoutType.LAYOUT_B_NO_PM25)
    harmonized = harmonize_layout(df, LayoutType.LAYOUT_B_NO_PM25)

    assert list(harmonized.columns) == CANONICAL_COLUMNS
    assert harmonized.iloc[0]["stasiun"] == "val_lokasi_spku"
    assert harmonized.iloc[0]["pm25"] == ""


def test_harmonize_layout_b():
    """Verify Layout B renames pm_10, pm_duakomalima, and lokasi_spku."""
    df = _make_dummy_row(LayoutType.LAYOUT_B)
    harmonized = harmonize_layout(df, LayoutType.LAYOUT_B)

    assert list(harmonized.columns) == CANONICAL_COLUMNS
    assert harmonized.iloc[0]["stasiun"] == "val_lokasi_spku"
    assert harmonized.iloc[0]["pm10"] == "val_pm_10"
    assert harmonized.iloc[0]["pm25"] == "val_pm_duakomalima"


def test_harmonize_layout_c():
    """Verify Layout C translates Indonesian column names to canonical."""
    df = _make_dummy_row(LayoutType.LAYOUT_C)
    harmonized = harmonize_layout(df, LayoutType.LAYOUT_C)

    assert list(harmonized.columns) == CANONICAL_COLUMNS
    assert harmonized.iloc[0]["pm10"] == "val_pm_sepuluh"
    assert harmonized.iloc[0]["pm25"] == "val_pm_duakomalima"
    assert harmonized.iloc[0]["so2"] == "val_sulfur_dioksida"
    assert harmonized.iloc[0]["co"] == "val_karbon_monoksida"
    assert harmonized.iloc[0]["o3"] == "val_ozon"
    assert harmonized.iloc[0]["no2"] == "val_nitrogen_dioksida"
    assert harmonized.iloc[0]["critical"] == "val_parameter_pencemar_kritis"


def test_harmonize_layout_c_bulan():
    """Verify Layout C+Bulan drops the redundant bulan column and harmonizes."""
    df = _make_dummy_row(LayoutType.LAYOUT_C_BULAN)
    harmonized = harmonize_layout(df, LayoutType.LAYOUT_C_BULAN)

    assert list(harmonized.columns) == CANONICAL_COLUMNS
    assert "bulan" not in harmonized.columns
    assert harmonized.iloc[0]["pm10"] == "val_pm_sepuluh"


def test_all_layouts_produce_exact_same_columns():
    """Verify that all 6 layouts produce identical CANONICAL_COLUMNS."""
    for layout in LayoutType:
        df = _make_dummy_row(layout)
        harmonized = harmonize_layout(df, layout)
        assert list(harmonized.columns) == CANONICAL_COLUMNS


def test_harmonize_quarantine_preserves_reason_and_canonical_columns():
    """Verify that quarantine rows produce QUARANTINE_COLUMNS across all layouts."""
    for layout in LayoutType:
        df = _make_dummy_row(layout)
        df["quarantine_reason"] = "TEST_REASON"
        harmonized = harmonize_layout(df, layout, is_quarantine=True)
        assert list(harmonized.columns) == QUARANTINE_COLUMNS
        assert harmonized.iloc[0]["quarantine_reason"] == "TEST_REASON"


def test_dispatch_and_validate_e2e_all_actual_files():
    """End-to-end integration test verifying that all 9 actual files output CANONICAL_COLUMNS."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw not found")

    actual_files = list(raw_dir.glob("*.xls"))
    assert len(actual_files) == 9

    for file_path in actual_files:
        result = dispatch_and_validate(file_path)
        assert len(result.valid) > 0
        assert list(result.valid.columns) == CANONICAL_COLUMNS
        if len(result.quarantined) > 0:
            assert list(result.quarantined.columns) == QUARANTINE_COLUMNS
