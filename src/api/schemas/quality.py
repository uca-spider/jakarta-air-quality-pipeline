"""Data-quality summary schema, derived from the Bronze raw tables."""

from pydantic import BaseModel


class QualitySummaryRow(BaseModel):
    """Per-source-file valid vs quarantined row counts and dominant reason."""

    source_file: str
    valid_rows: int
    quarantined_rows: int
    dominant_reason: str | None = None
