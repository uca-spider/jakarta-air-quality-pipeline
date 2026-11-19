"""BigQuery loader for the Jakarta ISPU ingestion pipeline.

Loads harmonized valid rows into aq_raw.ispu and quarantined rows into
aq_raw.ispu_quarantine. Each load is idempotent: existing rows with the
same file_hash are deleted before inserting the new batch.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from src.ingestion.models import ValidationResult

_DATASET = "aq_raw"
_TABLE_VALID = "ispu"
_TABLE_QUARANTINE = "ispu_quarantine"


def compute_file_hash(path: Path) -> str:
    """Return the MD5 hex digest of a file's contents."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def _delete_existing(client: bigquery.Client, project: str, table: str, file_hash: str) -> None:
    """Delete rows previously loaded from the same source file if table exists."""
    query = (
        f"DELETE FROM `{project}.{_DATASET}.{table}` "
        f"WHERE file_hash = '{file_hash}'"
    )
    try:
        client.query(query).result()
    except NotFound:
        # Table does not exist yet (first-time load); nothing to delete.
        pass


def load_to_bigquery(
    result: ValidationResult,
    source_file: Path,
    project: str,
) -> None:
    """Upload valid and quarantined rows to BigQuery.

    Args:
        result:      ValidationResult containing valid and quarantined DataFrames.
        source_file: Path to the source file (used for metadata).
        project:     GCP project ID.
    """
    client = bigquery.Client(project=project)
    file_hash = compute_file_hash(source_file)
    loaded_at = datetime.now(timezone.utc).isoformat()

    # --- valid rows ---
    valid_df = result.valid.copy()
    valid_df["source_file"] = source_file.name
    valid_df["file_hash"] = file_hash
    valid_df["loaded_at"] = loaded_at

    _delete_existing(client, project, _TABLE_VALID, file_hash)
    client.load_table_from_dataframe(
        valid_df,
        f"{project}.{_DATASET}.{_TABLE_VALID}",
    ).result()

    # --- quarantined rows (skip if none) ---
    if result.quarantined.empty:
        return

    q_df = result.quarantined.copy()
    q_df["source_file"] = source_file.name
    q_df["file_hash"] = file_hash
    q_df["loaded_at"] = loaded_at

    _delete_existing(client, project, _TABLE_QUARANTINE, file_hash)
    client.load_table_from_dataframe(
        q_df,
        f"{project}.{_DATASET}.{_TABLE_QUARANTINE}",
    ).result()
