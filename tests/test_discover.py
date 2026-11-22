"""Tests for the GCS new-file discovery runner (src/ingestion/discover.py).

Strategy:
- Mock the GCS and BigQuery clients so tests run without real GCP credentials.
- Patch the existing engine entry points (dispatch_and_validate, load_to_bigquery)
  and compute_file_hash so tests exercise discovery ORCHESTRATION, not parsing.
- No real file IO: blob downloads and hashing are mocked.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from google.cloud.exceptions import NotFound

from src.ingestion.discover import (
    DiscoveryResult,
    discovery_exit_code,
    fetch_loaded_hashes,
    iter_candidate_blobs,
    main,
    run_discovery,
)


def _blob(name: str) -> MagicMock:
    blob = MagicMock()
    blob.name = name
    return blob


# ---------------------------------------------------------------------------
# fetch_loaded_hashes
# ---------------------------------------------------------------------------

def test_fetch_loaded_hashes_returns_set():
    client = MagicMock()
    client.query.return_value.result.return_value = [
        {"file_hash": "h1"},
        {"file_hash": "h2"},
    ]
    assert fetch_loaded_hashes(client, "proj") == {"h1", "h2"}


def test_fetch_loaded_hashes_unions_valid_and_quarantine_tables():
    client = MagicMock()
    client.query.return_value.result.return_value = []
    fetch_loaded_hashes(client, "proj")
    sql = client.query.call_args[0][0]
    assert "aq_raw.ispu" in sql
    assert "aq_raw.ispu_quarantine" in sql


def test_fetch_loaded_hashes_empty_when_tables_missing():
    client = MagicMock()
    client.query.side_effect = NotFound("no table")
    assert fetch_loaded_hashes(client, "proj") == set()


# ---------------------------------------------------------------------------
# iter_candidate_blobs
# ---------------------------------------------------------------------------

def test_iter_candidate_blobs_filters_by_extension():
    client = MagicMock()
    client.list_blobs.return_value = [
        _blob("raw/ispu-2026.xls"),
        _blob("raw/notes.txt"),
        _blob("raw/"),  # folder placeholder
        _blob("raw/page.html"),
    ]
    names = [b.name for b in iter_candidate_blobs(client, "bkt")]
    assert names == ["raw/ispu-2026.xls", "raw/page.html"]


# ---------------------------------------------------------------------------
# run_discovery
# ---------------------------------------------------------------------------

@patch("src.ingestion.discover.load_to_bigquery")
@patch("src.ingestion.discover.dispatch_and_validate")
@patch("src.ingestion.discover.compute_file_hash")
def test_run_discovery_loads_only_new(mock_hash, mock_dispatch, mock_load, tmp_path):
    hashes = {"new.xls": "hNEW", "old.xls": "hOLD"}
    mock_hash.side_effect = lambda p: hashes[Path(p).name]

    storage_client = MagicMock()
    storage_client.list_blobs.return_value = [_blob("raw/new.xls"), _blob("raw/old.xls")]
    bq_client = MagicMock()
    bq_client.query.return_value.result.return_value = [{"file_hash": "hOLD"}]

    result = run_discovery(storage_client, bq_client, "bkt", "proj", tmp_path)

    assert result.loaded == ["new.xls"]
    assert result.skipped == ["old.xls"]
    assert result.failed == []
    assert mock_dispatch.call_count == 1
    assert mock_load.call_count == 1


@patch("src.ingestion.discover.load_to_bigquery")
@patch("src.ingestion.discover.dispatch_and_validate")
@patch("src.ingestion.discover.compute_file_hash")
def test_run_discovery_nothing_new(mock_hash, mock_dispatch, mock_load, tmp_path):
    mock_hash.return_value = "hOLD"
    storage_client = MagicMock()
    storage_client.list_blobs.return_value = [_blob("raw/old.xls")]
    bq_client = MagicMock()
    bq_client.query.return_value.result.return_value = [{"file_hash": "hOLD"}]

    result = run_discovery(storage_client, bq_client, "bkt", "proj", tmp_path)

    assert result.loaded == []
    assert result.failed == []
    assert mock_dispatch.call_count == 0


@patch("src.ingestion.discover.load_to_bigquery")
@patch("src.ingestion.discover.dispatch_and_validate")
@patch("src.ingestion.discover.compute_file_hash")
def test_run_discovery_continues_past_error_then_reports(
    mock_hash, mock_dispatch, mock_load, tmp_path
):
    mock_hash.side_effect = lambda p: Path(p).name  # unique hash per file, none loaded

    def fake_dispatch(path):
        if Path(path).name == "bad.xls":
            raise NotImplementedError("unknown layout")
        return MagicMock()

    mock_dispatch.side_effect = fake_dispatch

    storage_client = MagicMock()
    storage_client.list_blobs.return_value = [_blob("raw/good.xls"), _blob("raw/bad.xls")]
    bq_client = MagicMock()
    bq_client.query.return_value.result.return_value = []

    result = run_discovery(storage_client, bq_client, "bkt", "proj", tmp_path)

    assert result.loaded == ["good.xls"]  # good one still loaded
    assert [name for name, _ in result.failed] == ["bad.xls"]
    assert mock_load.call_count == 1


# ---------------------------------------------------------------------------
# discovery_exit_code
# ---------------------------------------------------------------------------

def test_exit_code_zero_when_no_failures():
    assert discovery_exit_code(DiscoveryResult(loaded=["a.xls"], skipped=[], failed=[])) == 0


def test_exit_code_one_when_any_failure():
    assert discovery_exit_code(
        DiscoveryResult(loaded=[], skipped=[], failed=[("bad.xls", "boom")])
    ) == 1


# ---------------------------------------------------------------------------
# main (entrypoint wiring + exit code)
# ---------------------------------------------------------------------------

@patch("src.ingestion.discover.run_discovery")
@patch("src.ingestion.discover.bigquery.Client")
@patch("src.ingestion.discover.storage.Client")
def test_main_returns_one_on_failure(mock_storage, mock_bq, mock_run, monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "proj")
    monkeypatch.setenv("RAW_BUCKET", "bkt")
    mock_run.return_value = DiscoveryResult(loaded=[], skipped=[], failed=[("bad.xls", "boom")])
    assert main([]) == 1


@patch("src.ingestion.discover.run_discovery")
@patch("src.ingestion.discover.bigquery.Client")
@patch("src.ingestion.discover.storage.Client")
def test_main_returns_zero_on_nothing_new(mock_storage, mock_bq, mock_run, monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "proj")
    monkeypatch.setenv("RAW_BUCKET", "bkt")
    mock_run.return_value = DiscoveryResult(loaded=[], skipped=["old.xls"], failed=[])
    assert main([]) == 0
