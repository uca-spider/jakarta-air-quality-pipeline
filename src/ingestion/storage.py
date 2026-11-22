"""Module to upload raw source files to Google Cloud Storage landing bucket."""

from datetime import datetime, timezone
from pathlib import Path
from google.cloud import storage

from src.ingestion.loader import compute_file_hash


def upload_file_to_gcs(
    source_path: Path,
    bucket_name: str,
    destination_folder: str = "raw",
    project: str | None = None,
) -> str:
    """Uploads a local raw file to the specified GCS bucket.

    Args:
        source_path: Path to the local file to upload.
        bucket_name: GCS bucket name.
        destination_folder: Subfolder in bucket (default: "raw").
        project: Optional GCP Project ID.

    Returns:
        str: The full GCS URI (e.g. gs://hudza-aq-raw/raw/ISPU_2017.xls).
    """
    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)

    blob_path = f"{destination_folder}/{source_path.name}" if destination_folder else source_path.name
    blob = bucket.blob(blob_path)

    file_hash = compute_file_hash(source_path)
    blob.metadata = {
        "file_hash": file_hash,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "original_filename": source_path.name,
    }

    blob.upload_from_filename(str(source_path))

    return f"gs://{bucket_name}/{blob_path}"
