"""Unit tests for ISPU 2017 HTML reader."""

import io
import pytest
import pandas as pd
from src.ingestion.reader_2017 import read_ispu_2017_html, EXPECTED_COLUMNS_2017
from src.ingestion.models import LayoutMismatchError


def test_read_ispu_2017_html_preserves_tokens_and_types():
    html = """
    <table>
      <thead>
        <tr><th>periode_data</th><th>tanggal</th><th>stasiun</th><th>pm10</th><th>so2</th>
            <th>co</th><th>o3</th><th>no2</th><th>max</th><th>critical</th><th>categori</th></tr>
      </thead>
      <tbody>
        <tr><td>201701</td><td>2017-01-25</td><td>DKI5 (KEBON JERUK)</td><td>6</td><td>11</td>
            <td>28</td><td>23</td><td>3</td><td>28</td><td>CO</td><td>BAIK</td></tr>
        <tr><td>201702</td><td>2017-02-02</td><td>DKI1 (BUNDERAN HI)</td><td>49</td><td>---</td>
            <td>23</td><td>41</td><td>3</td><td>49</td><td>PM10</td><td>BAIK</td></tr>
        <tr><td>201703</td><td>2017-03-01</td><td>DKI2 (KELAPA GADING)</td><td></td><td>---</td>
            <td></td><td></td><td></td><td>0</td><td></td><td>TIDAK ADA DATA</td></tr>
      </tbody>
    </table>
    """
    df = read_ispu_2017_html(io.StringIO(html))

    assert list(df.columns) == EXPECTED_COLUMNS_2017
    assert len(df) == 3

    # Invariants: preserve raw string tokens, no conversion to NaN or float
    assert df.loc[1, "so2"] == "---"
    assert df.loc[2, "pm10"] == ""
    assert df.loc[2, "critical"] == ""
    assert df.loc[0, "pm10"] == "6"
    assert df.loc[2, "max"] == "0"
    assert all(str(dtype) in ("object", "str", "string") for dtype in df.dtypes)
    assert all(isinstance(val, str) for val in df.values.flatten())


def test_read_ispu_2017_html_rejects_invalid_layout():
    html_wrong = """
    <table>
      <thead>
        <tr><th>periode_data</th><th>tanggal</th><th>wrong_col</th></tr>
      </thead>
      <tbody>
        <tr><td>201701</td><td>2017-01-01</td><td>val</td></tr>
      </tbody>
    </table>
    """
    with pytest.raises(LayoutMismatchError) as exc_info:
        read_ispu_2017_html(io.StringIO(html_wrong))
    assert "Layout mismatch" in str(exc_info.value)


def test_read_ispu_2017_html_rejects_empty_html():
    html_empty = "<html><body><p>No table here</p></body></html>"
    with pytest.raises(LayoutMismatchError) as exc_info:
        read_ispu_2017_html(io.StringIO(html_empty))
    assert "No table found" in str(exc_info.value)
