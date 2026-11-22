# REST API (Serving Layer)

A FastAPI service that serves the Jakarta ISPU Gold marts. It is **deploy-ready**
(containerized, env-configured) and runs in an offline **sample** mode by default,
so the API and its Swagger docs work with **zero GCP setup**.

## Architecture

```
routers (HTTP) -> dependencies -> repositories -> data source
                                   |- SampleRepository  (bundled JSON fixtures)
                                   |- LiveRepository    (BigQuery, cost-aware SQL)
```

- `API_DATA_MODE=sample` (default): serves small synthetic fixtures under
  `src/api/repositories/sample_data/`.
- `API_DATA_MODE=live`: queries BigQuery via Application Default Credentials
  (keyless / Workload Identity). Daily queries filter the monthly partition
  (`measurement_date`) and cluster key (`station_id`) to minimise bytes scanned;
  trends read the pre-aggregated monthly mart.

## Run it

```bash
# Docker (sample mode, no GCP needed)
docker compose up api        # -> http://localhost:8000/docs

# Local
uv run uvicorn src.api.main:app --reload       # sample mode
API_DATA_MODE=live uv run uvicorn src.api.main:app --reload   # BigQuery (needs ADC)
```

## Endpoints

| Method & path | Description |
|---|---|
| `GET /health` | Liveness; `?ready=1` adds a data-source readiness check (503 if down). |
| `GET /meta/categories` | ISPU category bands and their numeric ranges. |
| `GET /stations` | List the 5 SPKU stations. |
| `GET /stations/{station_id}` | One station (404 if unknown). |
| `GET /stations/{station_id}/daily?start=&end=` | Daily ISPU series (bounded date range required). |
| `GET /stations/{station_id}/latest` | Most recent reading for a station. |
| `GET /stations/{station_id}/trends?year=` | Monthly trend metrics (optional year filter). |
| `GET /quality/summary` | Per-source-file valid vs quarantined counts + dominant reason. |

## Configuration (env vars, `API_` prefix)

| Variable | Default | Meaning |
|---|---|---|
| `API_DATA_MODE` | `sample` | `sample` (offline fixtures) or `live` (BigQuery). |
| `API_GCP_PROJECT` | `jakarta-air-quality` | GCP project for live queries. |
| `API_MARTS_DATASET` | `aq_marts` | Gold marts dataset. |
| `API_RAW_DATASET` | `aq_raw` | Bronze raw dataset (for `/quality/summary`). |
| `API_CORS_ORIGINS` | `["*"]` | Allowed CORS origins (JSON list). |
| `API_MAX_DAILY_RANGE_DAYS` | `366` | Max span accepted by `/daily` (guards query cost). |

> **Dashboards:** Looker Studio connects directly to the BigQuery marts (native
> connector), not through this API.
