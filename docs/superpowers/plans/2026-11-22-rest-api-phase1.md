# REST API (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lean FastAPI REST API that serves the Jakarta ISPU Gold marts, runnable with zero GCP setup (sample mode) or against live BigQuery.

**Architecture:** Layered `routers → dependencies → repositories → data source`. A single `IspuRepository` Protocol has two backends — `SampleRepository` (bundled JSON fixtures) and `LiveRepository` (BigQuery, cost-aware SQL) — selected by config (`API_DATA_MODE`). Pydantic schemas are the public contract; ISPU category labels are derived from the numeric index by a shared service.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pydantic-settings, uvicorn, google-cloud-bigquery (already present), pytest + FastAPI TestClient + httpx.

**Spec:** `docs/superpowers/specs/2026-11-22-fullstack-api-ai-design.md` (Phase 1 only; Phase 2 forecasting is a separate plan).

## Global Constraints

- Python 3.12, full type hints; module docstrings; mirror `src/ingestion/` style.
- Code and comments in English.
- Test-first (TDD) with **synthetic fixtures**, not real rows. Small steps, commit per task.
- Keyless auth only: `LiveRepository` uses Application Default Credentials. Never read/print/create credentials; no key files.
- Never commit data files (`data/`, `*.xls`, `*.csv`). Sample fixtures are small **synthetic** JSON under `src/api/repositories/sample_data/` and are source, not data dumps.
- The API never fabricates rows: missing days are absent/null, never invented.
- New dependencies (`fastapi`, `uvicorn[standard]`, `pydantic-settings`, `httpx`) require author approval before install (CLAUDE.md) — confirm at Task 1.
- Station key is `DKI1`–`DKI5`. Dataset names default: `aq_marts`, `aq_raw`; project default `jakarta-air-quality`. All overridable by env (`API_` prefix).
- ISPU bands (D2): 0–50 BAIK, 51–100 SEDANG, 101–200 TIDAK SEHAT, 201–300 SANGAT TIDAK SEHAT, >300 BERBAHAYA.

## Review Focus

- **Unknown `station_id`** (e.g. `DKI9`): must return `404`, not `500` or empty `200`. → Tasks 2, 4, 5.
- **`/daily` without a date range, or a range wider than the cap**: must return `422` with a clear message, never trigger an unbounded BigQuery scan. → Task 4.
- **BigQuery unreachable / query error in live mode**: must surface as `503`, not a raw `500` stack. → Task 2.
- **Data gaps** (sparse 2019/2022, missing days): returned as gaps (absent/null), never back-filled or fabricated. → Task 4.
- **Invalid `API_DATA_MODE`** (not `sample`/`live`): must fail fast at startup with a clear error, not silently default. → Task 1.

---

### Task 1: Config, app factory, and health endpoint

**Files:**
- Create: `src/api/__init__.py`, `src/api/config.py`, `src/api/main.py`, `src/api/routers/__init__.py`, `src/api/routers/health.py`
- Modify: `requirements.txt`
- Test: `tests/api/__init__.py`, `tests/api/test_config.py`, `tests/api/test_health.py`

**Interfaces:**
- Produces:
  - `Settings` (pydantic-settings `BaseSettings`, env prefix `API_`): `data_mode: Literal["sample","live"] = "sample"`, `gcp_project: str = "jakarta-air-quality"`, `marts_dataset: str = "aq_marts"`, `raw_dataset: str = "aq_raw"`, `cors_origins: list[str] = ["*"]`, `max_daily_range_days: int = 366`.
  - `get_settings() -> Settings` (cached via `functools.lru_cache`).
  - `create_app() -> FastAPI` in `main.py` (app factory; registers routers, CORS, OpenAPI metadata). Module-level `app = create_app()`.

- [ ] **Step 1: Confirm dependencies with author, then add to `requirements.txt`** — `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `httpx`. (Per CLAUDE.md, get the OK before installing.)

- [ ] **Step 2: Write failing tests**

```python
# test_config.py
def test_defaults_to_sample_mode():
    s = Settings()
    assert s.data_mode == "sample"

def test_invalid_mode_rejected(monkeypatch):
    monkeypatch.setenv("API_DATA_MODE", "banana")
    with pytest.raises(ValidationError):
        Settings()

# test_health.py
def test_health_ok():
    client = TestClient(create_app())
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

- [ ] **Step 3: Run tests, verify they fail** — `pytest tests/api -v` → import/definition errors.

- [ ] **Step 4: Implement `Settings`, `get_settings`, `create_app`, and `GET /health`.** Health returns `{"status": "ok", "mode": settings.data_mode}`. (Readiness/BigQuery reachability check is added in Task 2 once the repository exists.)

- [ ] **Step 5: Run tests, verify pass** — `pytest tests/api -v` → PASS.

- [ ] **Step 6: Commit** — `feat(api): add config, app factory, and health endpoint`.

---

### Task 2: Repository abstraction, dual-mode wiring, and stations resource

**Files:**
- Create: `src/api/repositories/__init__.py`, `src/api/repositories/base.py`, `src/api/repositories/sample_repo.py`, `src/api/repositories/live_repo.py`, `src/api/repositories/bigquery_client.py`, `src/api/repositories/sample_data/stations.json`, `src/api/dependencies.py`, `src/api/schemas/__init__.py`, `src/api/schemas/station.py`, `src/api/routers/stations.py`
- Modify: `src/api/main.py` (register stations router), `src/api/routers/health.py` (add readiness probe)
- Test: `tests/api/test_sample_repo.py`, `tests/api/test_live_repo.py`, `tests/api/test_stations_router.py`

**Interfaces:**
- Produces:
  - `Station` schema: `station_id: str`, `name: str`, `district: str`, `latitude: float`, `longitude: float`.
  - `IspuRepository` Protocol with `get_stations() -> list[Station]` and `get_station(station_id: str) -> Station | None` (more methods added in later tasks).
  - `RepositoryError(Exception)` — raised by backends on data-source failure.
  - `SampleRepository` (reads `sample_data/*.json`) and `LiveRepository(client, settings)` (BigQuery) implementing the Protocol.
  - `get_repository() -> IspuRepository` in `dependencies.py` (selects backend by `get_settings().data_mode`, cached).
  - `make_bigquery_client(project: str) -> bigquery.Client` in `bigquery_client.py`.
- Consumes: Task 1 `Settings`, `get_settings`, `create_app`.

- [ ] **Step 1: Write failing tests**

```python
# test_sample_repo.py
def test_get_stations_returns_five():
    repo = SampleRepository()
    assert len(repo.get_stations()) == 5
def test_get_station_unknown_returns_none():
    assert SampleRepository().get_station("DKI9") is None

# test_live_repo.py — mock bigquery.Client (pattern from ingestion loader tests)
def test_get_stations_queries_marts_dataset(mock_bq_client):
    repo = LiveRepository(mock_bq_client, settings)
    repo.get_stations()
    sql = mock_bq_client.query.call_args[0][0]
    assert "aq_marts.dim_stations" in sql
def test_query_error_raises_repository_error(mock_bq_client):
    mock_bq_client.query.side_effect = GoogleAPIError("boom")
    with pytest.raises(RepositoryError):
        LiveRepository(mock_bq_client, settings).get_stations()

# test_stations_router.py — sample mode via dependency override
def test_list_stations_200(): ...                 # GET /stations -> 200, list of 5
def test_get_unknown_station_404(): ...            # GET /stations/DKI9 -> 404
def test_readiness_503_when_repo_down(): ...       # GET /health?ready=1 maps RepositoryError -> 503
```

- [ ] **Step 2: Run tests, verify fail.**

- [ ] **Step 3: Implement the Protocol, `RepositoryError`, both backends, `get_repository`, `Station` schema, and the stations router** (`GET /stations`, `GET /stations/{station_id}` → `404` when `None`). Create 5 synthetic `stations.json` entries. Add a readiness probe to `/health` that calls `get_stations()` and maps `RepositoryError → 503`. Register an exception handler mapping `RepositoryError → 503`.

- [ ] **Step 4: Run tests, verify pass.**

- [ ] **Step 5: Commit** — `feat(api): add repository abstraction, dual-mode wiring, and stations endpoints`.

---

### Task 3: ISPU category service and meta endpoint

**Files:**
- Create: `src/api/services/__init__.py`, `src/api/services/ispu_categories.py`, `src/api/routers/meta.py`
- Modify: `src/api/main.py` (register meta router)
- Test: `tests/api/test_ispu_categories.py`, `tests/api/test_meta_router.py`

**Interfaces:**
- Produces:
  - `classify_index(index: int | None) -> str | None` — None in, None out; band label otherwise.
  - `ISPU_BANDS: list[Band]` where `Band` = `{label: str, min: int, max: int | None}` (BERBAHAYA has `max=None`).
  - `GET /meta/categories` returns `ISPU_BANDS`.

- [ ] **Step 1: Write failing tests** — `classify_index(45)=="BAIK"`, `75=="SEDANG"`, `150=="TIDAK SEHAT"`, `250=="SANGAT TIDAK SEHAT"`, `350=="BERBAHAYA"`, `None is None`; boundary `50=="BAIK"`, `51=="SEDANG"`. `GET /meta/categories` → 200 with 5 bands.

- [ ] **Step 2: Run tests, verify fail.**

- [ ] **Step 3: Implement `classify_index`, `ISPU_BANDS`, and the meta router.**

- [ ] **Step 4: Run tests, verify pass.**

- [ ] **Step 5: Commit** — `feat(api): add ISPU category service and meta endpoint`.

---

### Task 4: Daily measurements and latest-reading resource

**Files:**
- Create: `src/api/schemas/measurement.py`, `src/api/routers/measurements.py`, `src/api/repositories/sample_data/daily.json`
- Modify: `src/api/repositories/base.py`, `sample_repo.py`, `live_repo.py` (add methods), `src/api/main.py`
- Test: `tests/api/test_measurements_repo.py`, `tests/api/test_measurements_router.py`

**Interfaces:**
- Produces:
  - `DailyMeasurement` schema: `measurement_date: date`, `station_id: str`, `pm10/pm25/so2/co/o3/no2: int | None`, `max_index: int | None`, `critical: str | None`, `category: str | None`.
  - Repo methods: `get_daily_series(station_id: str, start: date, end: date) -> list[DailyMeasurement]`; `get_latest(station_id: str) -> DailyMeasurement | None`.
  - `GET /stations/{station_id}/daily?start=&end=` and `GET /stations/{station_id}/latest`.
- Consumes: Task 2 repository + `get_station` (for 404), Task 3 `classify_index` (derive `category` when absent).

- [ ] **Step 1: Write failing tests**

```python
# repo (sample + mocked live)
def test_daily_series_filters_by_station_and_range(): ...
def test_live_daily_sql_filters_partition_and_cluster(mock_bq_client):
    # SQL must constrain measurement_date (partition) AND station_id (cluster)
    ...
def test_gaps_not_fabricated(): ...  # missing day absent from the list, no synthetic row

# router
def test_daily_requires_date_range(): ...          # missing start/end -> 422
def test_daily_range_too_wide_422(): ...            # (end-start) > max_daily_range_days -> 422
def test_daily_start_after_end_422(): ...
def test_daily_unknown_station_404(): ...
def test_latest_returns_most_recent(): ...
```

- [ ] **Step 2: Run tests, verify fail.**

- [ ] **Step 3: Implement schemas, repo methods, and router.** Live SQL filters `measurement_date BETWEEN @start AND @end` (partition) and `station_id = @sid` (cluster), parameterized. Router validates: both dates required, `start <= end`, `(end - start).days <= settings.max_daily_range_days` else `422`; `404` if `get_station` is `None`. Derive `category` via `classify_index` only when the mart value is null; never invent pollutant values.

- [ ] **Step 4: Run tests, verify pass.**

- [ ] **Step 5: Commit** — `feat(api): add daily measurements and latest-reading endpoints`.

---

### Task 5: Monthly trends resource

**Files:**
- Create: `src/api/schemas/trend.py`, `src/api/routers/trends.py`, `src/api/repositories/sample_data/trends.json`
- Modify: `base.py`, `sample_repo.py`, `live_repo.py`, `main.py`
- Test: `tests/api/test_trends_repo.py`, `tests/api/test_trends_router.py`

**Interfaces:**
- Produces:
  - `MonthlyTrend` schema mirroring `fct_ispu_monthly_trends`: `station_id`, `year: int`, `month: int`, `pm25_avg/pm10_avg/...: float | None`, `measurement_days: int`, `unhealthy_days: int`, `unhealthy_days_pct: float`.
  - Repo method `get_monthly_trends(station_id: str, year: int | None) -> list[MonthlyTrend]`.
  - `GET /stations/{station_id}/trends?year=`.
- Consumes: Task 2 repository (+ `get_station` for 404).

- [ ] **Step 1: Write failing tests** — repo reads `aq_marts.fct_ispu_monthly_trends` (assert table name in live SQL; confirm it does NOT read `fct_ispu_daily`); router `404` on unknown station; `year` filter optional; results sorted by `(year, month)`.

- [ ] **Step 2: Run tests, verify fail.**

- [ ] **Step 3: Implement schema, repo method, router.**

- [ ] **Step 4: Run tests, verify pass.**

- [ ] **Step 5: Commit** — `feat(api): add monthly trends endpoint`.

---

### Task 6: Data-quality summary resource

**Files:**
- Create: `src/api/schemas/quality.py`, `src/api/routers/quality.py`, `src/api/repositories/sample_data/quality.json`
- Modify: `base.py`, `sample_repo.py`, `live_repo.py`, `main.py`
- Test: `tests/api/test_quality_repo.py`, `tests/api/test_quality_router.py`

**Interfaces:**
- Produces:
  - `QualitySummaryRow` schema: `source_file: str`, `valid_rows: int`, `quarantined_rows: int`, `dominant_reason: str | None`.
  - Repo method `get_quality_summary() -> list[QualitySummaryRow]`.
  - `GET /quality/summary`.
- Consumes: Task 2 repository. Reads `aq_raw.ispu` + `aq_raw.ispu_quarantine` (raw dataset, via `settings.raw_dataset`).

- [ ] **Step 1: Write failing tests** — live SQL aggregates valid vs quarantined per `source_file` and picks the dominant `quarantine_reason`; router returns 200 list in sample mode.

- [ ] **Step 2: Run tests, verify fail.**

- [ ] **Step 3: Implement schema, repo method (a grouped count query joining/union-ing the two raw tables by `source_file`), router.**

- [ ] **Step 4: Run tests, verify pass.**

- [ ] **Step 5: Commit** — `feat(api): add data-quality summary endpoint`.

---

### Task 7: Deployment wiring and documentation

**Files:**
- Modify: `docker-compose.yml` (add `api` service), `README.md` (API section)
- Create: `src/api/README.md` (optional: run instructions, env vars table)
- Test: `tests/api/test_app_wiring.py`

**Interfaces:**
- Consumes: Task 1 `create_app`; all routers from Tasks 2–6.

- [ ] **Step 1: Write failing test** — `test_openapi_lists_all_routes()` asserts the OpenAPI schema from `create_app()` includes `/stations`, `/stations/{station_id}`, `/stations/{station_id}/daily`, `/stations/{station_id}/latest`, `/stations/{station_id}/trends`, `/quality/summary`, `/meta/categories`, `/health`.

- [ ] **Step 2: Run test, verify fail** (until all routers are wired — should pass if Tasks 2–6 done; this is the regression guard).

- [ ] **Step 3: Add the `api` service to `docker-compose.yml`** (`uvicorn src.api.main:app --host 0.0.0.0 --port 8000`, `API_DATA_MODE=sample` default so it runs with no GCP). Document env vars and the Swagger URL (`/docs`) in README.

- [ ] **Step 4: Run full API suite** — `pytest tests/api -v` → all PASS.

- [ ] **Step 5: Commit** — `feat(api): wire api service into docker-compose and document usage`.

---

## Notes for the executor
- Mock BigQuery the way `tests/` already mocks the client for the ingestion loader — no live calls in tests.
- Keep sample fixtures tiny and synthetic (a handful of rows), not copied real data.
- `fct_ispu_daily` queries MUST filter on both the monthly partition key and the `station_id` cluster key — this is the DE showcase; a test asserts it.
