"""CLI runner for the Jakarta ISPU ingestion pipeline.

Usage:
    # Dry-run validation & summary
    python -m src.ingestion.cli --file data/raw/ISPU_2017.xls
    python -m src.ingestion.cli --dir data/raw/

    # Validate and load into BigQuery & GCS bucket
    python -m src.ingestion.cli --dir data/raw/ --load --project jakarta-air-quality --bucket hudza-aq-raw
"""

import argparse
import os
import sys
from pathlib import Path

from src.ingestion.dispatcher import dispatch_and_validate
from src.ingestion.loader import load_to_bigquery
from src.ingestion.storage import upload_file_to_gcs
from src.ingestion.models import LayoutMismatchError

# File extensions treated as HTML table sources
_SUPPORTED_EXTENSIONS = {".xls", ".html", ".htm"}


def _print_separator():
    print("─" * 50)


def process_file(
    path: Path,
    load: bool = False,
    project: str | None = None,
    bucket: str | None = None,
) -> bool:
    """Process a single file, print summary, and optionally load into BigQuery and GCS.

    Returns True when every requested step succeeded, False otherwise.
    """
    ok = True
    if not path.exists():
        print(f"[ERROR] File not found: {path.name}")
        return False

    try:
        result = dispatch_and_validate(path)
    except LayoutMismatchError as exc:
        print(f"[ERROR] Layout mismatch in {path.name}: {exc}")
        return False
    except Exception as exc:
        print(f"[ERROR] Failed to process {path.name}: {exc}")
        return False

    n_valid = len(result.valid)
    n_quarantine = len(result.quarantined)

    _print_separator()
    print(f" File      : {path.name}")
    print(f" Valid     : {n_valid} rows")
    print(f" Quarantine: {n_quarantine} rows")

    if load:
        if not project:
            print(f"[ERROR] BigQuery loading requested for {path.name}, but project is not specified.")
            _print_separator()
            return False

        # 1. Upload original raw file to GCS landing zone (Bronze backup)
        if bucket:
            try:
                gcs_uri = upload_file_to_gcs(path, bucket_name=bucket, project=project)
                print(f" [GCS] Uploaded raw file to {gcs_uri}")
            except Exception as exc:
                print(f"[WARNING] Failed to upload {path.name} to GCS: {exc}")
                ok = False

        # 2. Upload structured valid and quarantined rows into BigQuery
        try:
            load_to_bigquery(result, source_file=path, project=project)
            print(f" [BigQuery] Loaded to BigQuery ({project}.aq_raw.ispu: {n_valid} rows)")
            if n_quarantine > 0:
                print(f" [BigQuery] Loaded {n_quarantine} rows to aq_raw.ispu_quarantine")
        except Exception as exc:
            print(f"[ERROR] BigQuery load failed for {path.name}: {exc}")
            ok = False

    _print_separator()
    return ok


def process_dir(
    directory: Path,
    load: bool = False,
    project: str | None = None,
    bucket: str | None = None,
) -> int:
    """Process all supported files in a directory and print a summary per file.

    Returns the number of files that failed (0 when everything succeeded).
    """
    files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
    )

    if not files:
        print(f"[INFO] No supported files found in {directory}")
        return 0

    failed = 0
    for f in files:
        if not process_file(f, load=load, project=project, bucket=bucket):
            failed += 1

    print(f"\n{'─' * 50}")
    print(f" Directory : {directory}")
    print(f" Files     : {len(files)} processed, {failed} failed")
    if load and project:
        print(f" Target BQ : {project}.aq_raw")
    if load and bucket:
        print(f" Target GCS: gs://{bucket}/raw/")
    print(f"{'─' * 50}")
    return failed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="ispu-cli",
        description="Jakarta ISPU ingestion pipeline runner",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Path to a single HTML/XLS file")
    group.add_argument("--dir", type=Path, help="Path to a directory of files")

    parser.add_argument(
        "--load",
        action="store_true",
        help="Load validated data into BigQuery (and GCS if bucket is specified)",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="GCP Project ID (can also be set via GCP_PROJECT or GOOGLE_CLOUD_PROJECT env var)",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default=os.getenv("RAW_BUCKET"),
        help="GCS bucket name for raw landing backup (can also be set via RAW_BUCKET env var)",
    )

    args = parser.parse_args(argv)

    project = args.project or os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if args.load and not project:
        parser.error("--load requires --project or GCP_PROJECT/GOOGLE_CLOUD_PROJECT environment variable")

    bucket = args.bucket or os.getenv("RAW_BUCKET")

    if args.file:
        failed = 0 if process_file(args.file, load=args.load, project=project, bucket=bucket) else 1
    else:
        failed = process_dir(args.dir, load=args.load, project=project, bucket=bucket)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
