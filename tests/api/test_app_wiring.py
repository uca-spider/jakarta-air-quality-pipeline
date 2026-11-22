"""Regression guard: every Phase-1 route is wired into the app."""

from src.api.main import create_app

EXPECTED_PATHS = {
    "/health",
    "/meta/categories",
    "/stations",
    "/stations/{station_id}",
    "/stations/{station_id}/daily",
    "/stations/{station_id}/latest",
    "/stations/{station_id}/trends",
    "/quality/summary",
}


def test_openapi_lists_all_routes():
    paths = set(create_app().openapi()["paths"].keys())
    missing = EXPECTED_PATHS - paths
    assert not missing, f"missing routes: {missing}"
