# Jakarta Air Quality Pipeline

An end-to-end, production-grade ELT data pipeline that ingests, validates, harmonizes, and transforms heterogeneous ISPU (Air Pollution Standard Index / *Indeks Standar Pencemar Udara*) data published by the Jakarta Open Data Portal into clean, tested, and analytics-ready datasets in Google Cloud BigQuery.

The source datasets (2016–2025) span multiple layout variations, legacy HTML tables masked as `.xls`, disparate date formats, shifting station names, and data anomalies. This project demonstrates enterprise Data Engineering best practices: **strict schema auto-detection, schema harmonization, quarantine isolation (zero silent drops), automated infrastructure via Terraform, containerization with Docker & Docker Compose, and SQL modeling with dbt**.

---

## Current Status

- **Ingestion & Validation Engine:** Completed (78/78 tests passing with TDD).
- **Cloud Infrastructure (GCP + GitHub):** Fully provisioned via Terraform (Storage, BigQuery, IAM, WIF, GitHub repo).
- **Raw Layer Ingestion (BigQuery):** 9 files loaded successfully:
  - `aq_raw.ispu`: **14,770 valid rows**
  - `aq_raw.ispu_quarantine`: **401 quarantined rows**
- **dbt Transformation Layer:** Completed & tested (16/16 tests passing in 9 seconds):
  - `aq_staging.stg_ispu` (View): Cleaned, cast, station standardized (`DKI1`–`DKI5`), deduplicated.
  - `aq_marts.dim_stations` (Table): 5 SPKU stations with coordinates & administrative areas.
  - `aq_marts.fct_ispu_daily` (Table): Partitioned monthly on `measurement_date`, clustered on `station_id` and `category`.
  - `aq_marts.fct_ispu_monthly_trends` (Table): Monthly aggregations and unhealthy day percentages.
- **Containerization:** Fully packaged with Docker and Docker Compose.

---

## Architecture Overview

```
Jakarta Open Data Portal (ISPU 2016-2025: HTML-in-XLS files)
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ PYTHON INGESTION ENGINE (`src/ingestion/`)                      │
│ 1. Detector    : Header fingerprinting (6 layout variants)      │
│ 2. Validators  : Dual-date parsing, Excel serial, station codes │
│ 3. Quarantine  : Segregation of invalid rows + error reasons    │
│ 4. Harmonizer  : Canonical 12-column standardization            │
│ 5. Loader      : Idempotent BigQuery load (MD5 file hash)       │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ GOOGLE CLOUD STORAGE & BIGQUERY (Provisioned by Terraform)      │
│  ├── Cloud Storage : `hudza-aq-raw` (Bronze landing bucket)     │
│  ├── `aq_raw`      : `ispu` (14.7k rows) & `ispu_quarantine`   │
│  ├── `aq_staging`  : `stg_ispu` (clean views via dbt)           │
│  └── `aq_marts`    : `dim_stations`, `fct_ispu_daily` (dbt)     │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ CONTAINERIZATION & ORCHESTRATION                                │
│  ├── Docker / Compose : Reproducible local execution            │
│  ├── GitHub Actions   : Automated CI/CD test suite              │
│  └── Keyless Auth     : GCP Workload Identity Federation (WIF)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6 Layout Variants Handled

| Layout Type | Years | Key Structural Characteristics |
|---|---|---|
| `LAYOUT_A` | 2016, 2017, 2018, 2020 | 11 columns, no PM2.5, mixed date formats (ISO `YYYY-MM-DD` and `DD/MM/YYYY`) |
| `LAYOUT_A_PM25` | 2021 | 12 columns, includes PM2.5, non-numeric max tokens |
| `LAYOUT_B_NO_PM25` | 2019 | 11 columns, provincial aggregate, `lokasi_spku` at the end |
| `LAYOUT_B` | 2022 | 12 columns, includes PM2.5, dates encoded as Excel serial numbers (e.g. `44562`) |
| `LAYOUT_C` | 2023 | 12 columns, Indonesian headers (`pm_sepuluh`, `sulfur_dioksida`, etc.) |
| `LAYOUT_C_BULAN` | 2024–2025 | 13 columns, Indonesian headers + redundant `bulan` column, synthesizes dates from day numbers |

---

## Validation & Quarantine Summary

Every row is validated against strict domain and calendar rules. Invalid rows are preserved with original string tokens and routed to `aq_raw.ispu_quarantine` with an explicit reason code:

| File / Period | Layout | Valid Rows | Quarantined Rows | Root Cause / Reason Codes |
|---|---|---:|---:|---|
| **2016** | Layout A | 1,670 | 160 | `DATE_PERIOD_MISMATCH` (wrong month metadata in Sept/Dec) |
| **2017** | Layout A | 1,825 | 0 | Clean baseline (1 full year) |
| **2018** | Layout A | 1,825 | 0 | Slash date format (`DD/MM/YYYY`) standardized to ISO |
| **2019** | Layout B (No PM2.5) | 345 | 0 | Daily provincial summary table |
| **2020** | Layout A | 1,620 | 210 | `INVALID_STATION_CODE` (shifted columns in March) + `DATE_PERIOD_MISMATCH` (Nov) |
| **2021** | Layout A + PM2.5 | 1,824 | 1 | `NON_NUMERIC_MAX_VALUE` (token `'PM25'` in max column) |
| **2022** | Layout B | 336 | 29 | `INVALID_STATION_CODE` (station `'0'`) + 28 rows from Feb 2020 |
| **2023** | Layout C | 1,825 | 0 | Indonesian column naming mapped to canonical columns |
| **2024–2025** | Layout C (Bulan) | 3,500 | 1 | `INVALID_DATE_FORMAT` (impossible calendar date: September 31st) |
| **TOTAL** | | **14,770** | **401** | **100% accounted for, zero data loss** |

---

## Key Design Principles

1. **Zero Silent Drops:** Invalid rows are never dropped or silently fixed during ingestion; they are segregated into `ispu_quarantine` with reasons for full auditability.
2. **Preserve Raw Tokens:** Data in `aq_raw` retains its original string representation (e.g., `'---'`, `'N/A'`). Type-casting is deferred to dbt staging.
3. **Idempotent Ingestion:** Each file load computes an MD5 `file_hash`. Existing records with the same hash are deleted before insertion, preventing duplicates on repeated executions.
4. **Keyless Authentication:** GitHub Actions authenticates to Google Cloud via Workload Identity Federation (WIF) without storing service account JSON keys in repositories.
5. **Infrastructure as Code (IaC):** Cloud Storage, BigQuery datasets, IAM bindings, WIF pools, and GitHub repository variables are declared in Terraform.

---

## Quickstart & Execution

### Option A: Via Docker Compose (Recommended)

Docker Compose provides convenient shortcuts without needing to install Python or dbt locally:

```bash
# Run unit & integration test suite (78 tests)
docker compose run --rm test

# Ingest all raw data into BigQuery
docker compose run --rm ingest

# Run dbt transformations (Staging views + Marts tables)
docker compose run --rm dbt-run

# Run dbt automated data quality tests (16 tests)
docker compose run --rm dbt-test

# Run full end-to-end pipeline (Ingest -> dbt run -> dbt test)
docker compose run --rm pipeline
```

### Option B: Local CLI Execution (with Astral `uv`)

```bash
# Virtual environment setup
uv venv
uv pip install -r requirements.txt

# Run pytest
uv run pytest -v

# Run Ingestion CLI
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
uv run python -m src.ingestion.cli --dir data/raw/ --load --project jakarta-air-quality

# Run dbt
cd dbt
uv run dbt run --profiles-dir .
uv run dbt test --profiles-dir .
```

---

## Infrastructure Management (Terraform)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Fill in your GCP project_id, bucket name, etc.

terraform init
terraform apply
```

Resources managed:
- **Cloud Storage Bucket:** `hudza-aq-raw`
- **BigQuery Datasets:** `aq_raw`, `aq_staging`, `aq_marts` (Location: `asia-southeast2` Jakarta)
- **IAM & Security:** Service account `aq-ingest` + Workload Identity Pool
- **GitHub Provider:** Auto-creates GitHub repo and injects CI/CD variables (`GCP_WIF_PROVIDER`, `GCP_INGEST_SA`, `RAW_BUCKET`).

---

## Project Roadmap

- [x] **Data Profiling & Inventory:** Analyze all 9 files across 10 years (`docs/DATA_INVENTORY.md`)
- [x] **Infrastructure as Code:** Terraform for GCS, BigQuery datasets, IAM, and WIF
- [x] **Layout Detection:** Auto-fingerprint 6 layout types
- [x] **Validation Engine:** Modular validators with domain rules and date standardization
- [x] **Schema Harmonization:** Unify heterogeneous schemas to 12 canonical columns
- [x] **Quarantine Segregation:** Capture invalid rows with reason codes and metadata
- [x] **Idempotent Ingestion:** MD5 file-hash deduplication and BigQuery loader
- [x] **CLI Runner:** Terminal interface supporting dry-run and Cloud loading
- [x] **Cloud Ingestion Verification:** 14,770 valid & 401 quarantined rows loaded to BigQuery
- [x] **dbt Staging Models:** Type-casting, station ID extraction (`DKI1`–`DKI5`), and NULL handling
- [x] **dbt Marts Models:** Daily air quality metrics, station dimensions, and monthly trends
- [x] **dbt Data Quality Tests:** 16 automated tests covering uniqueness, not-null, and referential integrity
- [x] **Containerization:** Dockerfile and Docker Compose shortcuts (`test`, `ingest`, `dbt-run`, `dbt-test`, `pipeline`)
- [ ] **Automated Orchestration:** GitHub Actions workflow with WIF for scheduled weekly ingestion and dbt runs
