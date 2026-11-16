# ISPU 2017 Ingestion & Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a clean reader and validator for 2017 Jakarta ISPU HTML tables that preserves all raw tokens as strings and routes invalid rows to quarantine with reason codes.

**Architecture:** We separate I/O and parsing from data validation. The reader parses HTML tables with `pandas.read_html(..., dtype=str, keep_default_na=False)` and verifies column layout schema. The validator evaluates row-level business rules (valid station prefix `DKI1`–`DKI5`, valid ISO date, date-period alignment) and produces a `ValidationResult` dataclass holding `valid` and `quarantined` DataFrames.

**Tech Stack:** Python 3.12, pandas, lxml, pytest.

**Spec:** `docs/superpowers/specs/2026-11-08-ispu-2017-ingestion-design.md`

## Global Constraints

- Never commit data files (`data/`, `*.xls`, `*.csv`).
- Keep original string tokens untouched (`---`, empty strings, raw numbers); no casting to int/float.
- Use `pandas.read_html` with `lxml`, never `read_excel`.
- Invalid rows must never be silently dropped or altered; route them to quarantine with `quarantine_reason`.
- Unknown layout must raise `LayoutMismatchError`.
- Station validation must check prefix `r"^DKI[1-5]\b"`.

## Review Focus

1. **Shifted columns where station is numeric (e.g. March 2020 rows like `'73'`):** Must be quarantined with `INVALID_STATION_CODE`.
2. **Whitespace-only or empty station values:** Must be quarantined with `MISSING_OR_EMPTY_STATION`.
3. **Invalid calendar dates (e.g. leap year mismatch or `'2017-02-31'`):** Must be quarantined with `INVALID_DATE_FORMAT`.
4. **Date vs period mismatch (e.g. date `'2017-02-01'` with period `'201701'`):** Must be quarantined with `DATE_PERIOD_MISMATCH`.
5. **Raw missing markers like `'---'` and empty string `''`:** Must be preserved exactly as strings in both valid and quarantined DataFrames, never converted to `NaN`.

---

### Task 1: Dependencies and Core Data Models

**Files:**
- Modify: `requirements.txt`
- Create: `src/ingestion/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `src/ingestion/models.py:ValidationResult`: dataclass with `valid: pd.DataFrame` and `quarantined: pd.DataFrame`
  - `src/ingestion/models.py:LayoutMismatchError`: subclass of `ValueError`

- [ ] **Step 1: Write test for models and exception**

```python
# tests/test_models.py
import pandas as pd
from src.ingestion.models import ValidationResult, LayoutMismatchError

def test_validation_result_holds_dataframes():
    df_valid = pd.DataFrame({"stasiun": ["DKI1 (BUNDERAN HI)"]})
    df_quarantine = pd.DataFrame({"stasiun": ["73"], "quarantine_reason": ["INVALID_STATION_CODE"]})
    res = ValidationResult(valid=df_valid, quarantined=df_quarantine)
    assert len(res.valid) == 1
    assert len(res.quarantined) == 1
    assert res.quarantined.iloc[0]["quarantine_reason"] == "INVALID_STATION_CODE"

def test_layout_mismatch_error_is_value_error():
    err = LayoutMismatchError("Columns do not match expected layout")
    assert isinstance(err, ValueError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py`
Expected: FAIL with ModuleNotFoundError: No module named 'src.ingestion.models'

- [ ] **Step 3: Update `requirements.txt` and implement `src/ingestion/models.py`**

Add `lxml>=5.0.0` to `requirements.txt`.
Create `src/ingestion/models.py`:
```python
from dataclasses import dataclass
import pandas as pd

class LayoutMismatchError(ValueError):
    """Raised when the columns of a table do not match the expected layout."""
    pass

@dataclass(frozen=True)
class ValidationResult:
    valid: pd.DataFrame
    quarantined: pd.DataFrame
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py`
Expected: PASS

---

### Task 2: 2017 ISPU HTML Reader

**Files:**
- Create: `src/ingestion/reader_2017.py`
- Test: `tests/test_reader_2017.py`

**Interfaces:**
- Consumes: `src/ingestion/models.py:LayoutMismatchError`
- Produces: `src/ingestion/reader_2017.py:read_ispu_2017_html(source: str | Path | IO[str] | IO[bytes]) -> pd.DataFrame`
- Expected 11 columns: `periode_data`, `tanggal`, `stasiun`, `pm10`, `so2`, `co`, `o3`, `no2`, `max`, `critical`, `categori`

- [ ] **Step 1: Write tests for `read_ispu_2017_html`**

```python
# tests/test_reader_2017.py
import io
import pytest
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
    # Check that tokens are strictly strings and preserved
    assert df.loc[1, "so2"] == "---"
    assert df.loc[2, "pm10"] == ""
    assert df.loc[2, "critical"] == ""
    assert df.loc[0, "pm10"] == "6"
    assert all(df.dtypes == "object")

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
    with pytest.raises(LayoutMismatchError):
        read_ispu_2017_html(io.StringIO(html_wrong))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reader_2017.py`
Expected: FAIL with ModuleNotFoundError or ImportError

- [ ] **Step 3: Implement `read_ispu_2017_html` in `src/ingestion/reader_2017.py`**

```python
from pathlib import Path
from typing import IO
import pandas as pd
from src.ingestion.models import LayoutMismatchError

EXPECTED_COLUMNS_2017 = [
    "periode_data", "tanggal", "stasiun", "pm10", "so2",
    "co", "o3", "no2", "max", "critical", "categori"
]

def read_ispu_2017_html(source: str | Path | IO[str] | IO[bytes]) -> pd.DataFrame:
    tables = pd.read_html(
        source,
        flavor="lxml",
        dtype=str,
        keep_default_na=False
    )
    if not tables:
        raise LayoutMismatchError("No table found in HTML source")
    df = tables[0]
    # Strip whitespace from column names if any
    df.columns = [str(c).strip().lower() for c in df.columns]
    if list(df.columns) != EXPECTED_COLUMNS_2017:
        raise LayoutMismatchError(
            f"Layout mismatch. Expected {EXPECTED_COLUMNS_2017}, got {list(df.columns)}"
        )
    return df
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reader_2017.py`
Expected: PASS

---

### Task 3: 2017 ISPU Row Validator & Quarantine Routing

**Files:**
- Create: `src/ingestion/validator_2017.py`
- Test: `tests/test_validator_2017.py`

**Interfaces:**
- Consumes: `src/ingestion/models.py:ValidationResult`
- Produces: `src/ingestion/validator_2017.py:validate_ispu_2017(df: pd.DataFrame) -> ValidationResult`

**Validation Rules & Reasons:**
1. `MISSING_OR_EMPTY_STATION`: `stasiun` is empty or only whitespace.
2. `INVALID_STATION_CODE`: `stasiun` does not start with `r"^DKI[1-5]\b"`.
3. `INVALID_DATE_FORMAT`: `tanggal` cannot be parsed as valid `YYYY-MM-DD` date.
4. `DATE_PERIOD_MISMATCH`: `tanggal` YYYYMM does not equal `periode_data`.

- [ ] **Step 1: Write unit tests covering valid cases and all quarantine failure modes**

```python
# tests/test_validator_2017.py
import pandas as pd
from src.ingestion.validator_2017 import validate_ispu_2017

def make_sample_df(rows):
    cols = ["periode_data", "tanggal", "stasiun", "pm10", "so2", "co", "o3", "no2", "max", "critical", "categori"]
    return pd.DataFrame(rows, columns=cols)

def test_validate_clean_rows():
    data = [
        ["201701", "2017-01-01", "DKI1 (BUNDERAN HI)", "49", "---", "23", "41", "3", "49", "PM10", "BAIK"],
        ["201701", "2017-01-02", "DKI5 (KEBON JERUK)", "25", "10", "15", "30", "5", "30", "O3", "BAIK"]
    ]
    df = make_sample_df(data)
    res = validate_ispu_2017(df)
    assert len(res.valid) == 2
    assert len(res.quarantined) == 0

def test_quarantine_shifted_station_numeric():
    # Synthetic representation of March 2020 shifted row
    data = [
        ["202003", "2020-03-19", "73", "22", "27", "37", "9", "73", "1", "PM10", "SEDANG"]
    ]
    df = make_sample_df(data)
    res = validate_ispu_2017(df)
    assert len(res.valid) == 0
    assert len(res.quarantined) == 1
    assert res.quarantined.iloc[0]["quarantine_reason"] == "INVALID_STATION_CODE"

def test_quarantine_empty_station():
    data = [
        ["201701", "2017-01-01", "   ", "49", "10", "23", "41", "3", "49", "PM10", "BAIK"]
    ]
    df = make_sample_df(data)
    res = validate_ispu_2017(df)
    assert len(res.valid) == 0
    assert len(res.quarantined) == 1
    assert res.quarantined.iloc[0]["quarantine_reason"] == "MISSING_OR_EMPTY_STATION"

def test_quarantine_invalid_date_format():
    data = [
        ["201702", "2017-02-31", "DKI1 (BUNDERAN HI)", "49", "10", "23", "41", "3", "49", "PM10", "BAIK"]
    ]
    df = make_sample_df(data)
    res = validate_ispu_2017(df)
    assert len(res.valid) == 0
    assert len(res.quarantined) == 1
    assert res.quarantined.iloc[0]["quarantine_reason"] == "INVALID_DATE_FORMAT"

def test_quarantine_date_period_mismatch():
    data = [
        ["201701", "2017-02-01", "DKI1 (BUNDERAN HI)", "49", "10", "23", "41", "3", "49", "PM10", "BAIK"]
    ]
    df = make_sample_df(data)
    res = validate_ispu_2017(df)
    assert len(res.valid) == 0
    assert len(res.quarantined) == 1
    assert res.quarantined.iloc[0]["quarantine_reason"] == "DATE_PERIOD_MISMATCH"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_validator_2017.py`
Expected: FAIL with ModuleNotFoundError or ImportError

- [ ] **Step 3: Implement `validate_ispu_2017` in `src/ingestion/validator_2017.py`**

Implement deterministic row evaluation using vectorization or boolean masks, assigning error reason codes with a priority hierarchy:
1. `MISSING_OR_EMPTY_STATION`
2. `INVALID_STATION_CODE`
3. `INVALID_DATE_FORMAT`
4. `DATE_PERIOD_MISMATCH`

Return `ValidationResult(valid=valid_df.reset_index(drop=True), quarantined=quarantined_df.reset_index(drop=True))`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_validator_2017.py`
Expected: PASS

---

### Task 4: End-to-End Pipeline Smoke Test and Actual 2017 File Verification

**Files:**
- Create: `tests/test_pipeline_2017.py`
- Modify: `src/ingestion/__init__.py`

**Interfaces:**
- Exposes `read_ispu_2017_html`, `validate_ispu_2017`, `ValidationResult`, and `LayoutMismatchError` from `src.ingestion`.

- [ ] **Step 1: Write integration test**

```python
# tests/test_pipeline_2017.py
from pathlib import Path
from src.ingestion import read_ispu_2017_html, validate_ispu_2017

def test_e2e_pipeline_on_actual_2017_data():
    raw_file = Path("data/raw/stasiun-pemantau-kualitas-udara-(-spku)-tahun-2017-komponen-data.xls")
    if not raw_file.exists():
        return  # Skip if local file is absent (e.g. clean CI checkout)

    df_raw = read_ispu_2017_html(raw_file)
    assert len(df_raw) == 1825
    
    result = validate_ispu_2017(df_raw)
    # Based on docs/DATA_INVENTORY.md: 2017 has 1,825 expected clean rows (365 days x 5 stations)
    assert len(result.valid) == 1825
    assert len(result.quarantined) == 0
```

- [ ] **Step 2: Update `src/ingestion/__init__.py` with exports**

```python
from src.ingestion.models import ValidationResult, LayoutMismatchError
from src.ingestion.reader_2017 import read_ispu_2017_html, EXPECTED_COLUMNS_2017
from src.ingestion.validator_2017 import validate_ispu_2017

__all__ = [
    "ValidationResult",
    "LayoutMismatchError",
    "read_ispu_2017_html",
    "EXPECTED_COLUMNS_2017",
    "validate_ispu_2017",
]
```

- [ ] **Step 3: Run all pytest suites**

Run: `pytest -v`
Expected: All tests PASS.
