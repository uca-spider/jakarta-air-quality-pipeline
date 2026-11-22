"""Automated discovery and ingestion of new ISPU files from the GCS landing bucket.

Entry point for the weekly `check-new-files` GitHub Actions workflow
(`python -m src.ingestion.discover`). It scans `gs://<RAW_BUCKET>/raw/`, finds
source files whose content MD5 is not yet loaded into BigQuery, and ingests the
new ones through the existing engine (dispatch -> validate -> harmonize -> load).

Semantics:
- Finding nothing new is success (logs "nothing new", exit 0).
- Every new file is processed; valid ones are loaded even if another file fails.
- The run fails (exit 1) if any file errored, reporting the offending file(s).

GCS is the source of truth for automated runs. Local `data/raw/` ingestion is
handled by `src.ingestion.cli`, not here.
"""

import os
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from google.cloud import bigquery, storage
from google.cloud.exceptions import NotFound

from src.ingestion.dispatcher import dispatch_and_validate
from src.ingestion.loader import compute_file_hash, load_to_bigquery

# Bucket prefix holding the raw source tables, and the extensions we ingest.
_RAW_PREFIX = "raw/"
_SUPPORTED_EXTENSIONS = (".xls", ".html", ".htm")

_RAW_DATASET = "aq_raw"
_TABLE_VALID = "ispu"
_TABLE_QUARANTINE = "ispu_quarantine"


@dataclass
class DiscoveryResult:
    """Outcome of a discovery run."""

    loaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (filename, error)


def fetch_loaded_hashes(bq_client: bigquery.Client, project: str) -> set[str]:
    """Return the set of file_hash values already present in BigQuery.

    Unions the valid and quarantine tables. Returns an empty set if the tables
    do not exist yet (first-ever run).
    """
    sql = (
        f"SELECT file_hash FROM `{project}.{_RAW_DATASET}.{_TABLE_VALID}` "
        "UNION DISTINCT "
        f"SELECT file_hash FROM `{project}.{_RAW_DATASET}.{_TABLE_QUARANTINE}`"
    )
    try:
        return {row["file_hash"] for row in bq_client.query(sql).result()}
    except NotFound:
        return set()


def iter_candidate_blobs(
    storage_client: storage.Client, bucket_name: str
) -> Iterator:
    """Yield blobs under the raw prefix whose name is a supported source file."""
    for blob in storage_client.list_blobs(bucket_name, prefix=_RAW_PREFIX):
        if blob.name.lower().endswith(_SUPPORTED_EXTENSIONS):
            yield blob


def run_discovery(
    storage_client: storage.Client,
    bq_client: bigquery.Client,
    bucket_name: str,
    project: str,
    download_dir: Path,
) -> DiscoveryResult:
    """Ingest every not-yet-loaded blob, continuing past per-file errors.

    A file is "new" when its content MD5 is absent from BigQuery. New files are
    downloaded into ``download_dir`` (named by their original basename so the
    ``source_file`` column stays meaningful) and run through the existing engine.
    """
    loaded_hashes = fetch_loaded_hashes(bq_client, project)
    result = DiscoveryResult()

    for blob in iter_candidate_blobs(storage_client, bucket_name):
        name = Path(blob.name).name
        local_path = download_dir / name
        try:
            blob.download_to_filename(str(local_path))
            file_hash = compute_file_hash(local_path)
            if file_hash in loaded_hashes:
                result.skipped.append(name)
                continue
            validation = dispatch_and_validate(local_path)
            load_to_bigquery(validation, source_file=local_path, project=project)
            loaded_hashes.add(file_hash)
            result.loaded.append(name)
        except Exception as exc:  # noqa: BLE001 - collect and report, never swallow
            result.failed.append((name, str(exc)))

    return result


def discovery_exit_code(result: DiscoveryResult) -> int:
    """Return 0 when nothing failed, 1 when any file errored."""
    return 1 if result.failed else 0


def _print_summary(result: DiscoveryResult, bucket_name: str) -> None:
    print(f"[discover] Scanned gs://{bucket_name}/{_RAW_PREFIX}")
    if not result.loaded and not result.failed:
        print("[discover] nothing new (all files already loaded)")
    for name in result.loaded:
        print(f"[discover] LOADED    {name}")
    for name in result.skipped:
        print(f"[discover] skipped   {name} (already loaded)")
    for name, error in result.failed:
        print(f"[discover] FAILED    {name}: {error}")
    print(
        f"[discover] summary: {len(result.loaded)} loaded, "
        f"{len(result.skipped)} skipped, {len(result.failed)} failed"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code (0 ok, 1 on any failure)."""
    project = (
        os.getenv("GCP_PROJECT_ID")
        or os.getenv("GCP_PROJECT")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    bucket_name = os.getenv("RAW_BUCKET")

    if not project:
        print("[discover] ERROR: GCP_PROJECT_ID (or GCP_PROJECT) is not set.")
        return 1
    if not bucket_name:
        print("[discover] ERROR: RAW_BUCKET is not set.")
        return 1

    storage_client = storage.Client(project=project)
    bq_client = bigquery.Client(project=project)

    with tempfile.TemporaryDirectory(prefix="ispu-discover-") as tmp:
        result = run_discovery(
            storage_client, bq_client, bucket_name, project, Path(tmp)
        )

    _print_summary(result, bucket_name)
    return discovery_exit_code(result)


if __name__ == "__main__":
    sys.exit(main())
