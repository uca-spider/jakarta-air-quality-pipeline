# Jakarta Air Quality Pipeline

A data pipeline that turns the heterogeneous ISPU (air pollution standard index) files published by the Jakarta open data portal into one clean, tested, queryable dataset in BigQuery. The files are split by year and month, come in different formats, and change schema over time, so the project focuses on **ingestion of messy data, schema harmonization, quarantine of invalid rows, and data quality tests**.

Everything runs on Google Cloud, is provisioned with Terraform, and is scheduled with GitHub Actions using keyless authentication (Workload Identity Federation).

**Status:** early scaffold. Infrastructure and CI are defined. The data inventory, ingestion, dbt models and tests are not implemented yet. See the roadmap.

## Why this project

- The source files are inconsistent: separate files per period, mixed formats, and columns that appear in some years only.
- A pipeline has to handle that explicitly instead of assuming one clean table.
- New files appear over time, so the schedule checks for new files rather than polling continuously.

## Planned architecture

```
Jakarta open data portal (ISPU files: CSV / Excel, per year or month)
        |
        |  discover: list resources, compare with what is already loaded (by file hash)
        v
Cloud Storage  bronze/   files stored unchanged, path includes year and file hash
        |
        |  harmonize: per-version column mapping, type casting, date parsing
        v
BigQuery  aq_raw       one row per station per day, with source file and load time
          aq_staging   typed and deduplicated (dbt), plus a quarantine table
                       with the rows that failed validation and the reason
        |
        v
BigQuery  aq_marts     daily station facts, monthly trends (dbt tests)
```

Infrastructure (`terraform/`): raw bucket, three BigQuery datasets, a least-privilege service account, and a Workload Identity pool restricted to this repository.

Workflows (`.github/workflows/`):

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci.yml` | push, pull request | pytest, `terraform fmt -check`, `terraform validate` |
| `check_new_files.yml` | every Monday (UTC), or manually | finds files not yet loaded and loads them |

## Data and licensing

Source data comes from the Jakarta open data portal (Dinas Lingkungan Hidup DKI Jakarta). **The data files are not stored in this repository.** The license terms of the source datasets must be checked before redistributing anything. Record what you find in `docs/DATA_INVENTORY.md`.

## Setup

1. Create a GCP project and install Terraform.
2. `cp terraform/terraform.tfvars.example terraform/terraform.tfvars` and fill in your values.
3. Apply the infrastructure:
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```
4. In GitHub, open Settings, Secrets and variables, Actions, Variables, and add `GCP_PROJECT_ID`, plus the three values printed by `terraform output` (`GCP_WIF_PROVIDER`, `GCP_INGEST_SA`, `RAW_BUCKET`).
5. No service account key is created, and nothing secret is stored in the repository.

## Design decisions

- **File hash as identity.** A file is loaded once per distinct content, so re-running the workflow never duplicates data.
- **Quarantine instead of silent dropping.** Invalid rows go to a quarantine table with the reason, so data loss is visible and measurable.
- **Explicit schema versions.** Each known file layout has its own column mapping; an unknown layout fails the run instead of loading wrong data.
- **Keyless authentication and least privilege.** The ingestion account can write one bucket and two datasets, and run BigQuery jobs, nothing more.

## Known limitations

- GitHub Actions schedules are not exact and can be delayed.
- Scheduled workflows in public repositories can be disabled automatically after a long period without repository activity.
- Terraform state is local and is not committed.

## Roadmap

- [x] Terraform: bucket, datasets, service account, Workload Identity Federation
- [x] CI: tests and Terraform checks
- [ ] Data inventory (`docs/DATA_INVENTORY.md`)
- [ ] File discovery and bronze storage (idempotent by file hash)
- [ ] Schema harmonization with per-version mappings
- [ ] Quarantine table and validation rules
- [ ] dbt staging and marts with tests
- [ ] Results table (files, rows loaded, rows quarantined, workflow success rate)
