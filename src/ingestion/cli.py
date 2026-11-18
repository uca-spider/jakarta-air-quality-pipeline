"""CLI runner for the Jakarta ISPU ingestion pipeline.

Usage:
    python -m src.ingestion.cli --file data/raw/ISPU_2017.xls
    python -m src.ingestion.cli --dir data/raw/
"""

import argparse
import sys
from pathlib import Path

from src.ingestion.dispatcher import dispatch_and_validate
from src.ingestion.models import LayoutMismatchError

# File extensions treated as HTML table sources
_SUPPORTED_EXTENSIONS = {".xls", ".html", ".htm"}


def _print_separator():
    print("─" * 50)


def process_file(path: Path) -> None:
    """Process a single file and print a summary report."""
    if not path.exists():
        print(f"[ERROR] File not found: {path.name}")
        return

    try:
        result = dispatch_and_validate(path)
    except LayoutMismatchError as exc:
        print(f"[ERROR] Layout mismatch in {path.name}: {exc}")
        return
    except Exception as exc:
        print(f"[ERROR] Failed to process {path.name}: {exc}")
        return

    n_valid = len(result.valid)
    n_quarantine = len(result.quarantined)

    _print_separator()
    print(f" File      : {path.name}")
    print(f" Valid     : {n_valid} rows")
    print(f" Quarantine: {n_quarantine} rows")
    _print_separator()


def process_dir(directory: Path) -> None:
    """Process all supported files in a directory and print a summary per file."""
    files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
    )

    if not files:
        print(f"[INFO] No supported files found in {directory}")
        return

    total_valid = 0
    total_quarantine = 0

    for f in files:
        process_file(f)
        # accumulate totals (re-process would be wasteful; use simple print-and-count approach)

    print(f"\n{'─' * 50}")
    print(f" Directory : {directory}")
    print(f" Files     : {len(files)} processed")
    print(f"{'─' * 50}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="ispu-cli",
        description="Jakarta ISPU ingestion pipeline runner",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Path to a single HTML/XLS file")
    group.add_argument("--dir", type=Path, help="Path to a directory of files")

    args = parser.parse_args(argv)

    if args.file:
        process_file(args.file)
    else:
        process_dir(args.dir)


if __name__ == "__main__":
    main()
