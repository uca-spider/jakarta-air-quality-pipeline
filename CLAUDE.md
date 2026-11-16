# Jakarta Air Quality Pipeline

Pipeline that loads heterogeneous Jakarta ISPU files (HTML tables saved as .xls) into BigQuery. Focus: messy-data ingestion, schema harmonization per file layout, quarantine of invalid rows, data quality tests.

## Read first
- `docs/DATA_INVENTORY.md` is the source of truth about data problems. Read it before changing any ingestion code. If code and inventory disagree, tell me; do not silently pick one.

## Rules
- Never commit data files (`data/`, `*.xls`, `*.csv`). Source license is unchecked.
- Never read, print, or create credentials: no `.env`, no `credentials/`, no JSON keys. Auth is keyless (Workload Identity). Never run `terraform apply`.
- Raw layer keeps original tokens exactly as read (`---`, `-`, empty). Cleaning happens in a later step.
- Invalid rows go to a quarantine table with a reason code. Never drop or "fix" rows silently.
- Loads must be idempotent (file content hash is the identity).
- One parser per layout and year. An unknown layout must fail the run.
- Do not guess missing information (for example the station of March 2020 rows). Quarantine it.

## Working style
- Write the test first, using synthetic fixtures (not real rows), then the code.
- Small steps. After each step, explain the design choice in plain language.
- Ask before adding dependencies or changing infrastructure files.
- Python 3.12, type hints, pytest. Read the files with `pandas.read_html` (lxml), never `read_excel`.
- Code and comments in English. Explanations to me in Indonesian.