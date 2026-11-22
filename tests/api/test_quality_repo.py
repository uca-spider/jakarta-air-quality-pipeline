"""Tests for the data-quality summary repository methods."""

from unittest.mock import MagicMock

from src.api.config import Settings
from src.api.repositories.live_repo import LiveRepository
from src.api.repositories.sample_repo import SampleRepository
from src.api.schemas.quality import QualitySummaryRow


def test_sample_quality_summary_returns_rows():
    rows = SampleRepository().get_quality_summary()
    assert rows
    assert all(isinstance(r, QualitySummaryRow) for r in rows)


def test_live_quality_sql_reads_raw_tables():
    client = MagicMock()
    client.query.return_value.result.return_value = []
    repo = LiveRepository(client, Settings(data_mode="live"))
    repo.get_quality_summary()
    sql = client.query.call_args[0][0]
    assert "aq_raw.ispu" in sql
    assert "aq_raw.ispu_quarantine" in sql
    assert "quarantine_reason" in sql
