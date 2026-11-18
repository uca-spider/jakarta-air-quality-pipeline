"""Dispatcher module to route parsed ISPU DataFrames to layout-specific validators."""

from pathlib import Path
from typing import Callable, IO, Union
import pandas as pd
from src.ingestion.models import LayoutType, ValidationResult
from src.ingestion.detector import read_and_detect
from src.ingestion.validator_layout_a import validate_layout_a
from src.ingestion.validator_2021 import validate_layout_a_pm25
from src.ingestion.validator_layout_b import validate_layout_b
from src.ingestion.validator_layout_c import validate_layout_c
from src.ingestion.harmonizer import harmonize_layout

# Registry of layout validators
VALIDATOR_REGISTRY: dict[LayoutType, Callable[[pd.DataFrame], ValidationResult]] = {
    LayoutType.LAYOUT_A: validate_layout_a,
    LayoutType.LAYOUT_A_PM25: validate_layout_a_pm25,
    LayoutType.LAYOUT_B: validate_layout_b,
    LayoutType.LAYOUT_B_NO_PM25: validate_layout_b,
    LayoutType.LAYOUT_C: validate_layout_c,
    LayoutType.LAYOUT_C_BULAN: validate_layout_c,
}


def dispatch_and_validate(
    source: Union[str, Path, IO[str], IO[bytes]],
    harmonize: bool = True,
) -> ValidationResult:
    """Reads HTML table, detects layout, dispatches to validator, and optionally harmonizes valid rows.

    Args:
        source: File path, HTML string, or file-like object containing ISPU table.
        harmonize: Whether to standardize valid rows into CANONICAL_COLUMNS (default: True).

    Returns:
        ValidationResult: Segregated valid (optionally harmonized) and quarantined DataFrames.

    Raises:
        LayoutMismatchError: If table cannot be read or layout is unknown.
        NotImplementedError: If layout is known but validator has not been implemented yet.
    """
    layout, df = read_and_detect(source)

    validator = VALIDATOR_REGISTRY.get(layout)
    if validator is None:
        raise NotImplementedError(
            f"Validator for {layout.value} is not yet implemented. "
            f"Available validators: {[k.value for k in VALIDATOR_REGISTRY.keys()]}"
        )

    result = validator(df)

    if harmonize and not result.valid.empty:
        harmonized_valid = harmonize_layout(result.valid, layout)
        return ValidationResult(
            valid=harmonized_valid, quarantined=result.quarantined
        )

    return result
