"""ISPU Ingestion module."""

from src.ingestion.models import ValidationResult, LayoutMismatchError, LayoutType
from src.ingestion.detector import (
    EXPECTED_LAYOUT_COLUMNS,
    detect_layout,
    read_and_detect,
)
from src.ingestion.dispatcher import (
    VALIDATOR_REGISTRY,
    dispatch_and_validate,
)
from src.ingestion.reader_2017 import read_ispu_2017_html, EXPECTED_COLUMNS_2017
from src.ingestion.validator_2017 import validate_ispu_2017
from src.ingestion.validator_layout_a import validate_layout_a

__all__ = [
    "ValidationResult",
    "LayoutMismatchError",
    "LayoutType",
    "EXPECTED_LAYOUT_COLUMNS",
    "detect_layout",
    "read_and_detect",
    "VALIDATOR_REGISTRY",
    "dispatch_and_validate",
    "read_ispu_2017_html",
    "EXPECTED_COLUMNS_2017",
    "validate_ispu_2017",
    "validate_layout_a",
]
