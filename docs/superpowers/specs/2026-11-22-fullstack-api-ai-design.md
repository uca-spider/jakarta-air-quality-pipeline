# Design: Full-Stack Serving Layer (REST API + Predictive Model)

Status: Draft for approval
Date: 2026-11-22
Author: fulandi (with Claude)

## 1. Intent & Why

The pipeline already tells a strong **Data Engineering** story end-to-end:
messy ingestion → quarantine → Medallion marts in BigQuery. This initiative
adds the "last mile" — a serving layer that turns the Gold marts into
something a person can actually use — to demonstrate breadth beyond DE.

**Audience:** recruiters and technical reviewers evaluating the author's skill
in a short session (not Jakarta residents checking air quality). The product is
a **portfolio showcase**, not a public service.

**Primary skill on display:** Data Engineering. The REST API and the predictive
model are deliberately positioned as **value-add ("nilai plus")**, proving the
author can close the gap from raw data to a usable product without turning this
into a sprawling backend or ML project.

**What success looks like:** a reviewer can, in a few minutes, read clean and
conventional code, click through an auto-generated OpenAPI/Swagger page, and see
a serving layer that is obviously built on the existing marts — including one
honest, well-validated forecasting feature.

## 2. Goals / Non-Goals / Anti-Goals

### Goals
- A **lean, sharp** FastAPI REST API that maps cleanly to the three Gold marts
  (`dim_stations`, `fct_ispu_daily`, `fct_ispu_monthly_trends`).
- **Cost-aware BigQuery access** that visibly exploits the partitioning (monthly)
  and clustering (station) of `fct_ispu_daily`, and reads the pre-aggregated
  `fct_ispu_monthly_trends` instead of recomputing from daily data. This is where
  the DE skill is showcased inside the API.
- **Auto-generated OpenAPI/Swagger docs** as the clickable "demo surface".
- A **7-day-ahead predictive model** of the daily ISPU index (`max`) per station,
  served through a forecast endpoint, with the ISPU **category derived** from the
  predicted number using the documented bands.
- **Deploy-ready**: containerized, configured via environment variables, no hard
  dependency on being hosted. Cloud Run is a later, small step (out of scope now).
- Built **test-first (TDD)** with synthetic fixtures, consistent with the
  existing `src/ingestion` conventions (Python 3.12, type hints, pytest).

### Non-Goals (not now, but sensible later)
- A real live Cloud Run deployment (design for it; do not do it this phase).
- A front-end web UI. Swagger + Looker Studio are the visual surfaces.
- Authentication / API keys / rate limiting beyond trivial safeguards.
- A GenAI chat assistant. The AI feature is a **predictive model**, decided
  explicitly over a Gemini chat.

### Anti-Goals (would make this a failure even if it "works")
- A large, half-finished API (20 shallow endpoints). Fewer, complete, documented
  endpoints beat breadth.
- A forecasting feature that **implies false accuracy**. Air quality is noisy and
  the source data has real gaps; the value is correct methodology (honest
  baseline, backtesting, explicit uncertainty), not a magic number.
- Silent invention of data in the API (mirrors the pipeline's "never guess" rule).
- Serving dashboard data to Looker Studio through the REST API (wrong tool;
  see Decision D1).

## 3. Constraints (from CLAUDE.md and the existing project)
- Python 3.12, type hints, pytest. **Test first**, then code. Small steps.
- Code and comments in English; discussion with the author in Indonesian.
- Keyless auth (Workload Identity) — never read/print/create credentials.
  The API uses Application Default Credentials; no key files.
- **Ask before adding dependencies** — this project adds several (see §8).
- Never commit data files. Never run `terraform apply`.
- Idempotency / auditability ethos carries over: the API never fabricates rows.

## 4. Key Decisions

| ID | Decision | Reason |
|----|----------|--------|
| D1 | **Looker Studio connects directly to BigQuery marts** (optionally via a curated `aq_reporting` view), **not** through the REST API. The REST API serves programmatic/web consumers and the forecast. | Looker Studio has a native BigQuery connector; feeding it via REST is awkward. Using the right tool per need is itself a DE signal. *(Confirmed by author.)* |
| D2 | Forecast target is the **numeric `max` index**; the **category label is derived** from the prediction via standard ISPU bands (0–50 BAIK, 51–100 SEDANG, 101–200 TIDAK SEHAT, 201–300 SANGAT TIDAK SEHAT). One model → two outputs. | Simpler and more honest than training a separate classifier. |
| D3 | Horizon is **7 days ahead**, per station. | Author's choice. |
| D4 | **Layered architecture**: `routers → services → repositories → BigQuery`, with Pydantic `schemas` as the API contract. | Clear separation reads well to a backend reviewer; the repository layer isolates cost-aware SQL. |
| D5 | Config via **environment variables** (`pydantic-settings`), defaulting to the existing project/dataset names. | Deploy-ready without hosting; no secrets in code. |
| D6 | Forecasting uses a **lightweight, dependency-light approach with an explicit baseline** (seasonal-naive / persistence) and **rolling-origin backtesting** (MAE/RMSE reported). Exact model library is a Phase-2 decision (see Open Question OQ2). | Portfolio value is methodology, not a heavy ML stack. |
| D7 | Phased delivery: **Phase 1 = REST API over marts**; **Phase 2 = predictive model + forecast endpoint**. | Phase 2 depends on Phase 1's data-access and app scaffolding. |
| D8 | Forecast model is produced by an **offline training script** that writes a stored artifact (per station); the `/forecast` endpoint **only runs inference** on the loaded artifact. | Keeps request latency low and avoids per-request BigQuery scans/training; deploy-friendly. *(Author's call.)* |
| D9 | **Dual data-source mode** via config (`API_DATA_MODE=sample\|live`): a `live` mode queries BigQuery (ADC), and a `sample` mode serves a small bundled sample dataset so the API + Swagger run with **zero GCP setup**. A single repository interface with two backends. | Confirmed by author: recruiters can click a live Swagger demo without credentials; still showcases the real BigQuery path. |
| D10 | Forecasting library is **`statsmodels`** (classical time-series) with an explicit seasonal-naive/persistence **baseline** and rolling-origin backtesting. | Confirmed by author; lightweight, methodology-forward. Supersedes OQ2. |
| D11 | `GET /quality/summary` is a **standard (not optional)** endpoint. | Confirmed by author; ties serving layer to the quarantine / "zero silent drops" DE story. |

## 5. Proposed Folder Structure (`src/api/`)

Mirrors the module-docstring + type-hint style of `src/ingestion/`.

```
src/api/
├── __init__.py
├── main.py                 # FastAPI app factory; router registration; CORS; metadata for Swagger
├── config.py               # Settings via env vars (project id, dataset names, CORS origins)
├── dependencies.py         # Shared FastAPI deps: cached BigQuery client, common query params
├── schemas/                # Pydantic models = the public API contract
│   ├── __init__.py
│   ├── station.py          # Station, StationList
│   ├── measurement.py      # DailyMeasurement, DailySeries
│   ├── trend.py            # MonthlyTrend
│   └── forecast.py         # ForecastPoint, ForecastResponse   (Phase 2)
├── repositories/           # BigQuery data access — all SQL lives here (cost-aware)
│   ├── __init__.py
│   ├── bigquery_client.py  # client factory + typed query helper
│   ├── stations_repo.py
│   ├── measurements_repo.py
│   └── trends_repo.py
├── services/               # Business logic (framework-agnostic, easily unit-tested)
│   ├── __init__.py
│   ├── ispu_categories.py  # numeric index → ISPU band label (shared by API & forecast)
│   └── forecasting.py      # model training/inference orchestration   (Phase 2)
└── routers/                # Thin HTTP layer grouped by resource
    ├── __init__.py
    ├── health.py
    ├── stations.py
    ├── measurements.py
    ├── trends.py
    └── forecast.py         # (Phase 2)
```

Tests mirror this under `tests/api/` (`test_stations_repo.py`, `test_stations_router.py`, …),
using FastAPI `TestClient` + dependency overrides, and a mocked BigQuery client
(consistent with how ingestion tests mock GCS/BigQuery). No live BigQuery in tests.

## 6. Proposed Endpoints

Lean set, each backed by one mart. `station_id` is the stable key `DKI1`–`DKI5`.

### Phase 1 — serving the marts

| Method & Path | Purpose | Mart | Cost-aware note |
|---|---|---|---|
| `GET /health` | Liveness/readiness (and a cheap BigQuery reachability check on readiness). | — | — |
| `GET /stations` | List the 5 SPKU stations with district + coordinates. | `dim_stations` | Tiny dimension; trivial. |
| `GET /stations/{station_id}` | One station's metadata. | `dim_stations` | — |
| `GET /stations/{station_id}/daily?start=&end=` | Daily ISPU series for a station in a date range (index `max`, per-pollutant values, critical parameter, category). | `fct_ispu_daily` | Filters on `measurement_date` (partition) + `station_id` (cluster) → minimal bytes scanned. Date range **required/capped** to avoid full scans. |
| `GET /stations/{station_id}/latest` | Most recent available reading for a station (useful for dashboard "current" tiles). | `fct_ispu_daily` | Single-partition tail read. |
| `GET /stations/{station_id}/trends?year=` | Monthly trend metrics (avg/min/max per pollutant, unhealthy-days %, etc.). | `fct_ispu_monthly_trends` | Reads pre-aggregated mart, never recomputes from daily. |
| `GET /meta/categories` | Reference list of ISPU bands and their numeric ranges. | static | Documents D2's mapping for consumers. |

**DE flex (included — D11):**
| `GET /quality/summary` | Per-source-file counts of valid vs quarantined rows and dominant reason codes. | `aq_raw.ispu` / `ispu_quarantine` | Surfaces the project's "zero silent drops" story directly in the API — a strong DE signal. |

### Phase 2 — predictive model

| Method & Path | Purpose | Note |
|---|---|---|
| `GET /stations/{station_id}/forecast?horizon=7` | 7-day-ahead forecast of the daily `max` index, each day with the **derived category** and an **uncertainty interval**; response includes the backtest metric (e.g. MAE) and the baseline comparison so the number is presented honestly. | `horizon` capped (default 7). |

### Cross-cutting
- Consistent error model (`404` unknown station, `422` bad params via Pydantic,
  `503` when BigQuery is unreachable). No fabricated data on gaps — missing days
  are returned as explicit nulls/absent, never invented.
- CORS configurable via env (so a future front-end or Looker community connector
  can call it).
- OpenAPI metadata (title, description, tags, examples) tuned so the Swagger page
  reads as the showcase surface.

## 7. Data-access & correctness notes
- `fct_ispu_daily` is partitioned monthly and clustered by `station_id` (and
  category); all daily queries must filter on both to stay cheap — the repository
  layer enforces a required, bounded date range.
- Grain is 1 station/day in the marts; 2019 & 2022 are sparse daily-summary years
  with many missing days. The API reflects this honestly (gaps are gaps).
- Forecasting must account for these gaps (irregular history per station) — part
  of why an honest baseline + backtest matters (D6).

## 8. New dependencies (REQUIRES AUTHOR APPROVAL before install — CLAUDE.md)
- Phase 1: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `httpx` (TestClient).
  (`pydantic` v2 comes with FastAPI; `google-cloud-bigquery` already present.)
- Phase 2: `statsmodels` (per D10).

## 9. What is left to the builder
- Exact Pydantic field names/shapes (follow the mart column names).
- Exact SQL text in each repository (following the cost-aware rules in §7).
- Pagination/limit defaults and the date-range cap value.
- Swagger copy (titles, descriptions, examples).
- Phase-2 model details: feature engineering, how gaps are handled, where the
  trained artifact lives (recompute-on-request vs stored artifact), backtest split.

## 10. Open Questions — RESOLVED
All four questions from the builder-check have been answered by the author and
folded into the decisions above:
- **OQ1 → D1:** Looker Studio connects directly to BigQuery marts. ✅
- **OQ2 → D10:** Forecasting uses `statsmodels` + honest baseline. ✅
- **OQ3 → D11:** `GET /quality/summary` is included as a standard endpoint. ✅
- **OQ4 → D9:** Dual data-source mode (`sample` + `live`) so the API/Swagger run
  with zero GCP setup. ✅

No open questions remain. Ready for plan.
```
