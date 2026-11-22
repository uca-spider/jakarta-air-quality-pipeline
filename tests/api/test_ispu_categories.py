"""Tests for the ISPU index -> category classification service."""

import pytest

from src.api.services.ispu_categories import classify_index


@pytest.mark.parametrize(
    "index, expected",
    [
        (45, "BAIK"),
        (50, "BAIK"),
        (51, "SEDANG"),
        (75, "SEDANG"),
        (150, "TIDAK SEHAT"),
        (250, "SANGAT TIDAK SEHAT"),
        (350, "BERBAHAYA"),
    ],
)
def test_classify_index_bands(index, expected):
    assert classify_index(index) == expected


def test_classify_none_returns_none():
    assert classify_index(None) is None
