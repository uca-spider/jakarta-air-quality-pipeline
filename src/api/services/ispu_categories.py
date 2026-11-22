"""ISPU index -> category classification (standard Indonesian ISPU bands).

Bands (inclusive): 0-50 BAIK, 51-100 SEDANG, 101-200 TIDAK SEHAT,
201-300 SANGAT TIDAK SEHAT, >300 BERBAHAYA.
"""

from pydantic import BaseModel


class Band(BaseModel):
    """One ISPU category band and its numeric index range."""

    label: str
    min: int
    max: int | None  # None = open-ended upper bound (BERBAHAYA)


ISPU_BANDS: list[Band] = [
    Band(label="BAIK", min=0, max=50),
    Band(label="SEDANG", min=51, max=100),
    Band(label="TIDAK SEHAT", min=101, max=200),
    Band(label="SANGAT TIDAK SEHAT", min=201, max=300),
    Band(label="BERBAHAYA", min=301, max=None),
]


def classify_index(index: int | None) -> str | None:
    """Return the ISPU category label for a numeric index, or None if index is None."""
    if index is None:
        return None
    for band in ISPU_BANDS:
        if band.max is None or index <= band.max:
            return band.label
    return ISPU_BANDS[-1].label


def derive_category(stored: str | None, max_index: int | None) -> str | None:
    """Keep the stored category if present; otherwise derive it from the index.

    Never invents a category when neither is available (both None -> None).
    """
    return stored if stored is not None else classify_index(max_index)
