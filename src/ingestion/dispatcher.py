"""Dispatcher module to route parsed ISPU DataFrames to layout-specific validators."""

from pathlib import Path
from typing import Callable, IO, Union
import pandas as pd
from src.ingestion.models import LayoutType, ValidationResult
from src.ingestion.detector import read_and_detect
from src.ingestion.validator_layout_a import validate_layout_a

# Registry of layout validators
VALIDATOR_REGISTRY: dict[LayoutType, Callable[[pd.DataFrame], ValidationResult]] = {
    LayoutType.LAYOUT_A: validate_layout_a,
}


def dispatch_and_validate(
    source: Union[str, Path, IO[str], IO[bytes]]
) -> ValidationResult:
    """Reads HTML table, detects layout, and dispatches to appropriate validator.

    Args:
        source: File path, HTML string, or file-like object containing ISPU table.

    Returns:
        ValidationResult: Segregated valid and quarantined DataFrames.

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

    return validator(df)
