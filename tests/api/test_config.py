"""Tests for API settings loaded from environment variables."""

import pytest
from pydantic import ValidationError

from src.api.config import Settings


def test_defaults_to_sample_mode():
    s = Settings()
    assert s.data_mode == "sample"


def test_invalid_mode_rejected(monkeypatch):
    monkeypatch.setenv("API_DATA_MODE", "banana")
    with pytest.raises(ValidationError):
        Settings()
