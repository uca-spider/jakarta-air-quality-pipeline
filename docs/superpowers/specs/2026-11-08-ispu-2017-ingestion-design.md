# Design Document: ISPU 2017 Ingestion & Validation

## 1. Intent and Why
The Jakarta Open Data portal provides air pollution standard index (ISPU) files saved as `.xls` files, but they are actually HTML tables with varying schemas, shifted columns, and messy tokens.
Step 1 establishes the baseline clean ingestion and validation pipeline for the 2017 dataset (Layout A), ensuring:
1. Raw string preservation (no token loss, no silent type casting).
2. Explicit layout validation (fails fast if an unexpected format is provided).
3. Deterministic row validation routing invalid rows to a quarantine dataset with explicit error reason codes.
4. Clean separation of concerns between file reading and data validation so every component can be tested independently with synthetic fixtures.

## 2. Requirements & Constraints
- **Python version:** 3.12, strict type hints, pytest.
- **HTML Parsing:** `pandas.read_html` with `lxml` engine. Never `read_excel`.
- **Dependency:** Add `lxml>=5.0.0` to `requirements.txt`.
- **Raw Layer Invariant:** All columns read as strings (`dtype=str`, `keep_default_na=False`). No casting, no trimming, no `NaN` imputation in the reader.
- **Station Validation:** Validate station codes using regex prefix `r"^DKI[1-5]\b"`. Any station not matching DKI1–DKI5 is quarantined.
- **Quarantine Invariant:** Never drop or fix invalid rows silently. Retain original columns plus `quarantine_reason`.
- **Output Interface:** Return `ValidationResult` dataclass with `valid: pd.DataFrame` and `quarantined: pd.DataFrame`.

## 3. Interfaces and Signatures

### Data Models (`src/ingestion/models.py`)
```python
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class ValidationResult:
    valid: pd.DataFrame
    quarantined: pd.DataFrame
```

### Reader (`src/ingestion/reader_2017.py`)
```python
EXPECTED_COLUMNS_2017 = [
    "periode_data", "tanggal", "stasiun", "pm10", "so2",
    "co", "o3", "no2", "max", "critical", "categori"
]

class LayoutMismatchError(ValueError):
    """Raised when HTML table columns do not match expected 2017 Layout A."""
    pass

def read_ispu_2017_html(source: str | Path | IO[str] | IO[bytes]) -> pd.DataFrame:
    """Reads a 2017 ISPU HTML file into a DataFrame, keeping all raw string tokens."""
    ...
```

### Validator (`src/ingestion/validator_2017.py`)
```python
def validate_ispu_2017(df: pd.DataFrame) -> ValidationResult:
    """Validates raw 2017 ISPU DataFrame and segregates rows into valid and quarantined."""
    ...
```

## 4. Quarantine Reason Codes
- `MISSING_OR_EMPTY_STATION`: Empty or whitespace-only station value.
- `INVALID_STATION_CODE`: Station does not start with `DKI1` to `DKI5` (e.g. numeric `73` from March 2020 shifted rows).
- `INVALID_DATE_FORMAT`: Date string is not valid `YYYY-MM-DD`.
- `DATE_PERIOD_MISMATCH`: Date does not match `periode_data` (e.g., date `2017-02-01` but period `201701`).

## 5. Non-Goals for Step 1
- No numeric type casting (`pm10`, `max`, etc. remain `str`).
- No imputation or replacement of `---` or empty tokens.
- No database or GCP Cloud Storage integration.
- No parsing of 2018, 2020, 2022, or 2023 files yet.
