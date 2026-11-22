# Jakarta Air Quality Data Pipeline (ISPU 2016–2025)

[![CI Pipeline](https://github.com/uca-spider/jakarta-air-quality-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/uca-spider/jakarta-air-quality-pipeline/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![GCP](https://img.shields.io/badge/Google_Cloud-Storage_%26_BigQuery-red.svg)](https://cloud.google.com/)
[![dbt-bigquery](https://img.shields.io/badge/dbt-1.10-orange.svg)](https://www.getdbt.com/)
[![Terraform](https://img.shields.io/badge/Terraform-1.10-purple.svg)](https://www.terraform.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)

An end-to-end, production-grade **ELT Data Engineering Pipeline** that ingests, validates, harmonizes, and transforms 10 years of heterogeneous ISPU (*Indeks Standar Pencemar Udara* / Air Pollution Standard Index) data from the Jakarta Open Data Portal into an analytics-ready Medallion Lakehouse on **Google Cloud Platform (GCS & BigQuery)** using **dbt**, **Terraform**, and **Docker**.

---

## Executive Summary

Public environmental datasets in developing metropolises often suffer from severe structural drift over time. Jakarta's open air quality records (2016–2025) represent a prime real-world data engineering challenge:
- **HTML Masquerading as Excel:** Files with `.xls` extensions are actually legacy HTML `<table>` documents.
- **6 Structural Layouts:** Column counts range from 11 to 13; column names fluctuate between English acronyms and Indonesian descriptive terms (`pm10` vs `pm_sepuluh`).
- **Chaotic Temporal Representations:** Date values span standard ISO (`YYYY-MM-DD`), European slash formats (`DD/MM/YYYY`), 5-digit Excel serial floats (e.g. `44562.0`), Indonesian month-day pairs, and impossible calendar dates (e.g. September 31st).
- **Corrupted Records & String Noise:** Raw tables contain non-numeric measurement values (`'---'`, `'N/A'`, `'PM25'` inside max index columns) and shifted column values.

### Engineering Solution
This pipeline implements an enterprise **Medallion Architecture**:
1. **Bronze (Immutable Lake & Raw Data):** Raw files are archived unchanged in Google Cloud Storage (`gs://hudza-aq-raw/raw/`). The ingestion engine validates every row, routes defective records into an isolated **Quarantine Table** (preserving 100% auditability with zero silent drops), and loads clean data idempotently into BigQuery using MD5 file-hash identity.
2. **Silver (Cleaned & Standardized Staging):** Modeled in dbt as a high-performance view that parses data types, converts missing string tokens to SQL `NULL`, standardizes SPKU station identifiers (`DKI1`–`DKI5`), and deduplicates grain collisions.
3. **Gold (Analytical Data Marts):** Dimensional modeling with a station dimension (`dim_stations`), a daily fact table partitioned monthly and clustered (`fct_ispu_daily`), and pre-aggregated monthly trend metrics (`fct_ispu_monthly_trends`).
4. **Reliability & Automation:** Enforced by **80 Python unit & integration tests (100% TDD)**, **16 dbt schema & referential integrity tests**, keyless Workload Identity Federation (WIF), and reproducible containerization with Docker Compose.

---

## Medallion Architecture & Data Flow

```
 Jakarta Open Data Portal (10 Years ISPU Data: 2016 - 2025 HTML-in-XLS)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PYTHON INGESTION ENGINE (CLI)                         │
│  1. Storage Upload  : Archive raw file to GCS Data Lake (MD5 Checksum)      │
│  2. Layout Detector : Fingerprint header signatures across 6 layout types   │
│  3. Validators      : Strict domain checks (station codes, dates, numbers)  │
│  4. Harmonizer      : Map variant schemas into 12 canonical fields          │
│  5. Quarantine Box  : Segregate invalid rows with explicit error codes      │
│  6. Idempotent Load : MD5 deduplication before BigQuery write               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────────┐
│     BRONZE: GCS DATA LAKE            │  │      BRONZE: BIGQUERY RAW         │
│  `gs://hudza-aq-raw/raw/*.xls`       │  │  ├── `aq_raw.ispu` (14,770 rows)  │
│  (Immutable source-of-truth)         │  │  └── `aq_raw.ispu_quarantine`     │
│                                      │  │      (401 audit rows)             │
└──────────────────────────────────────┘  └─────────────────┬─────────────────┘
                                                            │
                                                            ▼ (dbt transformations)
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SILVER LAYER: BIGQUERY STAGING                          │
│  `aq_staging.stg_ispu` (View)                                               │
│  • Natural grain: (measurement_date, station_id) with MD5 surrogate key     │
│  • Type coercion (INT64 pollutants, DATE casting)                           │
│  • String token normalization ('---', 'N/A' -> NULL)                        │
│  • Station standardization ('DKI1 (Bunderan HI)' -> 'DKI1')                 │
│  • Deduplication via QUALIFY ROW_NUMBER() = 1                               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼ (dbt dimensional marts)
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GOLD LAYER: ANALYTICS MARTS                            │
│  ├── `aq_marts.dim_stations`                                                │
│  │   5 SPKU Stations, administrative districts, and GPS coordinates         │
│  ├── `aq_marts.fct_ispu_daily` (Partitioned by Month, Clustered by Station) │
│  │   Grain: 1 station/day. Primary metrics & categories                     │
│  └── `aq_marts.fct_ispu_monthly_trends`                                     │
│      Grain: 1 station/month. Rollups, critical parameters, % unhealthy days │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6 Layout Variants Handled

The ingestion engine automatically identifies and routes each incoming file through dedicated validators:

| Layout Variant | Scope / Years | Characteristics & Edge Cases | Resolution Strategy |
|---|---|---|---|
| `LAYOUT_A` | 2016, 2017, 2018, 2020 | 11 columns, no PM2.5. Mixed date formats (`YYYY-MM-DD` and `DD/MM/YYYY`). Shifted station columns in 2020. | Multi-pattern regex date parser; station code whitelist; quarantine column-shifted rows. |
| `LAYOUT_A_PM25` | 2021 | 12 columns, includes PM2.5. Non-numeric corrupt tokens inside numeric columns. | Validates numeric casting; quarantines records where `'PM25'` appears in max values. |
| `LAYOUT_B_NO_PM25` | 2019 | 11 columns, province-level summary report. Station column is named `lokasi_spku` at the end of the table. | Flexible column index mapping; standardizes column ordering to canonical order. |
| `LAYOUT_B` | 2022 | 12 columns, includes PM2.5. Dates encoded as raw Excel floating serial numbers (e.g. `44562`). Corrupted station codes (`'0'`). | Converts Excel serial numbers relative to `1899-12-30` epoch; isolates station `'0'` to quarantine. |
| `LAYOUT_C` | 2023 | 12 columns. Indonesian column names (`pm_sepuluh`, `sulfur_dioksida`, `karbon_monoksida`, `kategori`). | Header dictionary translation to canonical column schema. |
| `LAYOUT_C_BULAN` | 2024–2025 | 13 columns. Indonesian headers plus redundant `bulan` text column. Dates represented as numeric day of month (`1`–`31`). | Synthesizes full calendar dates from day number, month name, and target year; traps impossible dates (e.g. Sept 31st). |

---

## Validation Audit & Quarantine Summary

Zero data loss policy: **100% of rows are accounted for**. Invalid records are never silently dropped; they are stored in `aq_raw.ispu_quarantine` with full raw cell tokens and explicit audit failure reasons:

| Source File / Period | Layout Detected | Total Rows | Valid Rows | Quarantined Rows | Dominant Failure Reason Codes |
|---|---|---:|---:|---:|---|
| **2016** (`ispu-2016.xls`) | Layout A | 1,830 | 1,670 | 160 | `DATE_PERIOD_MISMATCH` (wrong month metadata in Sept & Dec) |
| **2017** (`ispu-2017.xls`) | Layout A | 1,825 | 1,825 | 0 | *Clean baseline (5 stations × 365 days)* |
| **2018** (`ispu-2018.xls`) | Layout A | 1,825 | 1,825 | 0 | *Clean (standardized slash dates to ISO)* |
| **2019** (`ispu-2019.xls`) | Layout B (No PM2.5) | 345 | 345 | 0 | *Clean daily provincial summary table* |
| **2020** (`ispu-2020.xls`) | Layout A | 1,830 | 1,620 | 210 | `INVALID_STATION_CODE` (shifted columns in March) + `DATE_PERIOD_MISMATCH` |
| **2021** (`ispu-2021.xls`) | Layout A + PM2.5 | 1,825 | 1,824 | 1 | `NON_NUMERIC_MAX_VALUE` (corrupted token `'PM25'` in max column) |
| **2022** (`ispu-2022.xls`) | Layout B | 365 | 336 | 29 | `INVALID_STATION_CODE` (station code `'0'`) + 28 duplicate rows from Feb 2020 |
| **2023** (`ispu-2023.xls`) | Layout C | 1,825 | 1,825 | 0 | *Clean (Indonesian headers translated to canonical)* |
| **2024–2025** (`ispu-komponen.xls`) | Layout C (Bulan) | 3,501 | 3,500 | 1 | `INVALID_DATE_FORMAT` (impossible calendar date: September 31st) |
| **TOTAL** | | **15,171** | **14,770** | **401** | **100% accounted for, 0 silent drops** |

---

## Data Modeling & dbt Architecture

### 1. Canonical Raw Schema (`aq_raw.ispu`)
The raw ingestion harmonizer ensures that all 6 layouts conform to a uniform 12-column raw contract:
`tanggal`, `stasiun`, `pm10`, `pm25`, `so2`, `co`, `o3`, `no2`, `max`, `critical`, `kategori`, `file_hash`, `ingested_at`.

### 2. Staging Layer (`aq_staging.stg_ispu`)
- **Primary Surrogate Key:** `MD5(CONCAT(measurement_date, '_', station_id))`
- **Deduplication:** Applied window function `ROW_NUMBER() OVER (PARTITION BY measurement_date, station_id ORDER BY ingested_at DESC) = 1`.
- **Station Normalization:** Maps raw station variations (`DKI1 (Bunderan HI)`, `DKI1`, etc.) to strict keys: `DKI1`, `DKI2`, `DKI3`, `DKI4`, `DKI5`.
- **Type Coercion:** Safely converts string tokens (`'---'`, `'N/A'`, empty strings) to SQL `NULL` and casts pollutant columns to `INT64`.

### 3. Marts Layer (`aq_marts`)
- **`dim_stations` (Dimension):** Static master data for Jakarta's 5 official Air Quality Monitoring Stations (SPKU):
  - `DKI1`: Bundaran HI, Menteng (Jakarta Pusat) - [-6.1950, 106.8230]
  - `DKI2`: Kelapa Gading (Jakarta Utara) - [-6.1600, 106.9000]
  - `DKI3`: Jagakarsa (Jakarta Selatan) - [-6.3330, 106.8330]
  - `DKI4`: Lubang Buaya, Cipayung (Jakarta Timur) - [-6.2890, 106.8990]
  - `DKI5`: Kebon Jeruk (Jakarta Barat) - [-6.1930, 106.7700]
- **`fct_ispu_daily` (Fact):** Daily station measurements. Optimized for analytics with:
  - **Partitioning:** Monthly by `measurement_date` (minimizes query bytes scanned).
  - **Clustering:** By `station_id` and `category` (accelerates station and air quality category filters).
- **`fct_ispu_monthly_trends` (Fact Mart):** Pre-aggregated monthly analytical summary:
  - Average, minimum, and maximum values per pollutant (`pm25_avg`, `pm10_avg`, etc.).
  - Total measurement days and count of unhealthy days (`TIDAK SEHAT`, `SANGAT TIDAK SEHAT`, `BERBAHAYA`).
  - Monthly percentage of unhealthy days (`unhealthy_days_pct`).

---

## Testing & Quality Gates

The project enforces quality at both the Python application layer and the SQL transformation layer:

```
Automated Test Suite: 96 / 96 Passing
├── Python Ingestion Tests (pytest) : 80 passed in 1.45s
│   ├── Layout Detector Tests      : 10 passed (synthetic fixtures + real samples)
│   ├── Layout Dispatcher Tests    : 4 passed (routing and invalid format traps)
│   ├── Schema Harmonizer Tests    : 8 passed (canonical 12-column compliance)
│   ├── Layout Validators Tests    : 34 passed (Layout A, B, C, date parsing, quarantine)
│   ├── GCS Storage Backup Tests   : 4 passed (upload, metadata, mock client)
│   ├── BigQuery Loader Tests      : 11 passed (MD5 idempotency, NotFound handling)
│   └── Ingestion CLI Tests        : 9 passed (flags, dry-run, load orchestration)
│
└── dbt Data Quality Tests         : 16 passed in 9.00s
    ├── `stg_ispu`                 : unique surrogate key, not null checks, accepted categories
    ├── `dim_stations`             : unique station_id, not null checks, coordinate validation
    ├── `fct_ispu_daily`           : composite uniqueness, foreign key relationship to dim_stations
    └── `fct_ispu_monthly_trends`  : unique station-month grain, positive value constraints
```

---

## Infrastructure as Code (Terraform)

All cloud resources are provisioned via Terraform with zero manual console configuration:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

**Managed Infrastructure:**
- **Google Cloud Storage:** `hudza-aq-raw` (Bronze landing bucket in `asia-southeast2` Jakarta).
- **Google BigQuery Datasets:** `aq_raw`, `aq_staging`, and `aq_marts` (Location: `asia-southeast2`).
- **Identity & Access Management (IAM):** Least-privilege service account `aq-ingest@jakarta-air-quality.iam.gserviceaccount.com`.
- **Workload Identity Federation (WIF):** Keyless authentication pool linking GitHub Actions to GCP without long-lived private keys.
- **GitHub Provider:** Programmatically sets GitHub Actions repository variables (`GCP_WIF_PROVIDER`, `GCP_INGEST_SA`, `RAW_BUCKET`).

---

## Quickstart & Execution

### Prerequisites
- Docker & Docker Compose **OR** Python 3.12 with [Astral uv](https://github.com/astral-sh/uv).
- Google Cloud credentials with BigQuery and Storage permissions.

### Option A: Using Docker Compose (Zero local environment dependencies)

```bash
# 1. Run the entire Python test suite (80 tests)
docker compose run --rm test

# 2. Ingest raw data to GCS Bucket & BigQuery
docker compose run --rm ingest

# 3. Build dbt models (Staging view + Mart tables)
docker compose run --rm dbt-run

# 4. Run dbt data quality and constraint tests (16 tests)
docker compose run --rm dbt-test

# 5. Execute full end-to-end pipeline in one command
docker compose run --rm pipeline
```

### Option B: Local CLI Execution (with Astral `uv`)

```bash
# 1. Setup virtual environment & dependencies
uv venv
uv pip install -r requirements.txt

# 2. Run unit & integration tests
uv run pytest -v

# 3. Authenticate to Google Cloud
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"

# 4. Ingest raw data: backup to GCS and load to BigQuery
uv run python -m src.ingestion.cli \
  --dir data/raw/ \
  --load \
  --project jakarta-air-quality \
  --bucket hudza-aq-raw

# 5. Run dbt transformations & tests
cd dbt
uv run dbt run --profiles-dir .
uv run dbt test --profiles-dir .
```

---

## Repository Structure

```
jakarta-air-quality-pipeline/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Automated CI: pytest + Terraform format/validate
│       └── check_new_files.yml    # Weekly automated ingestion & dbt orchestration (WIF)
├── data/
│   └── raw/                       # Raw HTML-in-XLS files (git-ignored)
├── dbt/
│   ├── dbt_project.yml            # dbt project configuration
│   ├── profiles.yml               # BigQuery connection profiles (asia-southeast2)
│   ├── macros/
│   │   └── generate_schema_name.sql # Custom schema naming for clean dataset mapping
│   └── models/
│       ├── staging/
│       │   ├── sources.yml        # Raw BigQuery table declarations
│       │   ├── stg_ispu.sql       # Cleaned, typed, deduplicated staging view
│       │   └── stg_ispu.yml       # Automated schema & data quality tests
│       └── marts/
│           ├── dim_stations.sql   # SPKU station dimensions with coordinates
│           ├── fct_ispu_daily.sql # Partitioned & clustered daily ISPU fact table
│           ├── fct_ispu_monthly_trends.sql # Monthly rollup trend metrics
│           └── marts.yml          # Marts integrity & relationship tests
├── docs/
│   └── DATA_INVENTORY.md          # Comprehensive data profiling and layout analysis
├── src/
│   └── ingestion/
│       ├── __init__.py
│       ├── cli.py                 # CLI entry point (--file, --dir, --load, --bucket)
│       ├── detector.py            # Header signature layout detection
│       ├── dispatcher.py          # Validator routing and harmonization orchestrator
│       ├── harmonizer.py          # Canonical schema mapping and quarantine packaging
│       ├── loader.py              # Idempotent BigQuery loader (MD5 deduplication)
│       ├── models.py              # Pydantic / Typed data contracts
│       ├── storage.py             # GCS raw file archiver (Bronze Lake)
│       ├── validator_layout_a.py  # Validator for Layout A (2016-2020)
│       ├── validator_2021.py      # Validator for 2021 Layout A with PM2.5
│       ├── validator_layout_b.py  # Validator for Layout B (Excel serial dates)
│       └── validator_layout_c.py  # Validator for Layout C (Indonesian headers)
├── terraform/
│   ├── main.tf                    # GCP GCS, BigQuery, IAM & WIF declarations
│   ├── github.tf                  # GitHub provider & action variables integration
│   ├── variables.tf               # Terraform input variable definitions
│   └── outputs.tf                 # Output endpoints and IDs
├── tests/                         # Pytest test suite (80 unit & integration tests)
├── docker-compose.yml             # Local pipeline orchestration shortcuts
├── Dockerfile                     # Multi-stage container definition
├── pytest.ini                     # Pytest runner configuration
├── requirements.txt               # Pinned Python dependencies
└── README.md                      # Project documentation
```

---

## Project Roadmap

- [x] **Data Profiling & Schema Reverse-Engineering:** Audited 10 years of data (`docs/DATA_INVENTORY.md`).
- [x] **Infrastructure as Code:** Provisioned GCS, BigQuery datasets, IAM, and WIF via Terraform.
- [x] **Bronze Storage (Data Lake):** Raw files immutably archived in `gs://hudza-aq-raw/raw/`.
- [x] **Layout Detection Engine:** Automated fingerprinting across 6 distinct tabular layouts.
- [x] **Strict Validation Engine:** Date normalization, numeric checks, and station code validation.
- [x] **Quarantine Segregation:** Preserved 401 defective rows with reason codes; zero silent drops.
- [x] **Schema Harmonization:** Unified heterogeneous columns into 12 canonical attributes.
- [x] **Idempotent Ingestion:** MD5 file hash deduplication prevents duplicate loads.
- [x] **CLI Runner:** Configurable ingestion runner supporting local dry-run, GCS, and BigQuery.
- [x] **dbt Staging Models:** Data type casting, station code harmonization, and window deduplication.
- [x] **dbt Marts Models:** Designed `dim_stations`, partitioned `fct_ispu_daily`, and `fct_ispu_monthly_trends`.
- [x] **Automated Data Quality Testing:** 96 tests passing across Python unit tests and dbt constraints.
- [x] **Containerization:** Production Docker image and multi-service Docker Compose workflow.
- [x] **Keyless CI/CD:** GitHub Actions workflow with Google Cloud Workload Identity Federation (WIF).

---

## REST API (Serving Layer)

A **FastAPI** service (`src/api/`) serves the Gold marts over HTTP. It is deploy-ready (containerized, env-configured) and ships a dual data-source design:

- **`sample` mode (default):** serves small synthetic fixtures, so the API and its auto-generated Swagger docs run with **zero GCP setup** — ideal for a quick demo.
- **`live` mode:** queries BigQuery via keyless ADC, with **cost-aware SQL** (daily queries filter the monthly partition and `station_id` cluster key; trends read the pre-aggregated monthly mart).

```bash
docker compose up api          # -> http://localhost:8000/docs  (Swagger UI)
# or locally:
uv run uvicorn src.api.main:app --reload
```

| Method & path | Mart | Description |
|---|---|---|
| `GET /health` | — | Liveness; `?ready=1` checks the data source (503 if down). |
| `GET /meta/categories` | static | ISPU category bands and ranges. |
| `GET /stations` · `GET /stations/{id}` | `dim_stations` | Station list / one station (404 if unknown). |
| `GET /stations/{id}/daily?start=&end=` | `fct_ispu_daily` | Daily series (bounded date range). |
| `GET /stations/{id}/latest` | `fct_ispu_daily` | Most recent reading. |
| `GET /stations/{id}/trends?year=` | `fct_ispu_monthly_trends` | Monthly trend metrics. |
| `GET /quality/summary` | `aq_raw.*` | Valid vs quarantined counts per source file. |

**Dashboards:** Looker Studio connects directly to the BigQuery marts via its native connector, not through this API. See [`src/api/README.md`](src/api/README.md) for full configuration.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details. Raw air quality data is sourced from the [Jakarta Open Data Portal](https://data.jakarta.go.id/) under open government data terms.
