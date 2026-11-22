# Jakarta Air Quality Pipeline — Agent Guidelines

An end-to-end ELT data pipeline that ingests, validates, harmonizes, and transforms heterogeneous Jakarta ISPU (Air Pollution Standard Index / *Indeks Standar Pencemar Udara*) data (2016–2025) into Google Cloud Storage and BigQuery, followed by dbt transformations, containerization, and analytical marts.

---

## Read First
- `docs/DATA_INVENTORY.md` is the primary source of truth about raw data anomalies across all 9 source files. Read it before touching ingestion or validation logic. If code and inventory disagree, ask the user; do not silently pick one.
- `README.md` contains the complete architectural specification, 6-layout matrix, quarantine audit table, and test coverage metrics.

---

## Core Rules & Constraints
1. **Zero Silent Drops:** Invalid rows are never dropped or silently fixed. Route defective rows to `aq_raw.ispu_quarantine` with explicit reason codes (`DATE_PERIOD_MISMATCH`, `INVALID_STATION_CODE`, `NON_NUMERIC_MAX_VALUE`, `INVALID_DATE_FORMAT`, `DUPLICATE_DATE_STATION_IN_FILE`). The last one is a cross-row rule: when a `(measurement_date, station_id)` key repeats within a single file with differing values, the whole group is quarantined because picking one would be guessing.
2. **Preserve Raw Tokens:** Data in `aq_raw` retains original string representation (`---`, `-`, `N/A`, empty). Type-casting is strictly handled in dbt staging.
3. **Idempotent Ingestion:** Each file load computes an MD5 `file_hash`. Existing records with matching hash are deleted before insertion.
4. **Never Guess Missing Data:** Do not guess missing stations (e.g. March 2020) or synthesize dates without deterministic period context. Quarantine them.
5. **No Secret Commits:** Never commit data files (`data/`, `*.xls`, `*.csv`), credential files (`*.json`, `*.env`), or Terraform state.
6. **Auth is Keyless:** CI/CD uses Google Cloud Workload Identity Federation (WIF) without JSON keys in GitHub Secrets.
7. **File Parser:** All source `.xls` files are actually HTML `<table>` elements. Use `pandas.read_html` (with `lxml`), never `pandas.read_excel`.

---

## Architecture & Data Assets

### 1. Bronze Layer (Data Lake & Raw)
- **GCS Bucket:** `gs://hudza-aq-raw/raw/` (immutable backup of original XLS files with MD5 checksums).
- **BigQuery Dataset:** `aq_raw` (GCP Project: `jakarta-air-quality`, Location: `asia-southeast2` Jakarta).
  - `aq_raw.ispu`: 14,616 valid rows conforming to 12 canonical columns + `file_hash` + `ingested_at`.
  - `aq_raw.ispu_quarantine`: 555 defective rows conforming to canonical columns + `quarantine_reason` + `file_hash` + `ingested_at`.

### 2. Silver Layer (Staging)
- **BigQuery Dataset:** `aq_staging`
  - `aq_staging.stg_ispu` (View): Cleansed, types cast (`INT64`, `DATE`), station IDs normalized to `DKI1`–`DKI5`, missing tokens mapped to `NULL`, deduplicated across files with `QUALIFY ROW_NUMBER() OVER (PARTITION BY measurement_date, station_id ORDER BY <file whose year equals the date's year first>, ingested_at DESC, source_file DESC) = 1` (only December 2022 overlaps; the 2022 file wins).
  - `aq_staging.stg_ispu_rejects` (View): Every raw row that does NOT reach `stg_ispu`, with a `reject_reason` (`UNPARSEABLE_DATE`, `UNKNOWN_STATION`, `OVERLAP_ACROSS_FILES`). Makes the staging dedup explicit instead of a silent drop. The invariant `count(aq_raw.ispu) = count(stg_ispu) + count(stg_ispu_rejects)` is enforced by the dbt test `assert_staging_reconciles`.

### 3. Gold Layer (Analytics Marts)
- **BigQuery Dataset:** `aq_marts`
  - `aq_marts.dim_stations` (Table): 5 SPKU monitoring stations with administrative areas and GPS coordinates.
  - `aq_marts.fct_ispu_daily` (Table): Grain is `(measurement_date, station_id)`. Partitioned monthly by `measurement_date`, clustered by `station_id` and `category`.
  - `aq_marts.fct_ispu_monthly_trends` (Table): Grain is `(year_month, station_id)`. Monthly aggregations, min/max/avg, and unhealthy days percentage.

---

## Key Commands & Workflow

```bash
# Run Python Unit & Integration Tests (148 tests)
uv run pytest -v

# Run Ingestion CLI (Dry-run or Load to GCS + BigQuery)
uv run python -m src.ingestion.cli --dir data/raw/ --load --project jakarta-air-quality --bucket hudza-aq-raw

# Run dbt Models & Quality Tests (17 tests)
cd dbt && uv run dbt run --profiles-dir . && uv run dbt test --profiles-dir .

# Docker Compose Shortcuts
docker compose run --rm test
docker compose run --rm ingest
docker compose run --rm dbt-run
docker compose run --rm dbt-test
docker compose run --rm pipeline
```

---

## Working Style & Expectations
- **TDD (Test-Driven Development):** Write or update tests first using synthetic fixtures before writing implementation code.
- **Language Convention:** Code, docstrings, schema files, and commit messages in English. Explanations and communication with the user in clear, friendly Indonesian.
- **Next Planned Features:**
  1. Looker Studio BI Dashboard connected to `aq_marts`.
  2. Backend REST API with FastAPI (`src/api/`) for ISPU queries & station lookups.
  3. Web AI Application (Text-to-Insight / Conversational Agent using Gemini API).
