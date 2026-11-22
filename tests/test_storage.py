"""Tests for Google Cloud Storage upload module (src/ingestion/storage.py).

Strategy:
- Mock google.cloud.storage.Client so tests run without real GCP credentials
- Verify that upload_file_to_gcs uploads file to correct bucket and blob path
- Verify blob metadata (file_hash, uploaded_at) is set
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.ingestion.storage import upload_file_to_gcs


@patch("src.ingestion.storage.storage.Client")
def test_upload_file_to_gcs_uploads_blob(mock_storage_client_cls, tmp_path):
    """upload_file_to_gcs uploads the file to the raw/ folder with metadata."""
    sample_file = tmp_path / "ISPU_2017.xls"
    sample_file.write_bytes(b"dummy xls content")

    mock_client = MagicMock()
    mock_storage_client_cls.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    uri = upload_file_to_gcs(
        source_path=sample_file,
        bucket_name="hudza-aq-raw",
        destination_folder="raw",
    )

    mock_client.bucket.assert_called_once_with("hudza-aq-raw")
    mock_bucket.blob.assert_called_once_with("raw/ISPU_2017.xls")
    mock_blob.upload_from_filename.assert_called_once_with(str(sample_file))
    assert uri == "gs://hudza-aq-raw/raw/ISPU_2017.xls"
    assert "file_hash" in mock_blob.metadata
    assert "uploaded_at" in mock_blob.metadata


@patch("src.ingestion.storage.storage.Client")
def test_upload_file_to_gcs_raises_file_not_found(mock_storage_client_cls, tmp_path):
    """upload_file_to_gcs raises FileNotFoundError if file does not exist."""
    missing_file = tmp_path / "non_existent.xls"

    with pytest.raises(FileNotFoundError):
        upload_file_to_gcs(
            source_path=missing_file,
            bucket_name="hudza-aq-raw",
        )
