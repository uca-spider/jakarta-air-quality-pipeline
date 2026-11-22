"""FastAPI application factory for the Jakarta Air Quality REST API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_settings
from src.api.routers import health

API_TITLE = "Jakarta Air Quality API"
API_DESCRIPTION = (
    "REST API serving the Jakarta ISPU air-quality Gold marts "
    "(stations, daily measurements, monthly trends, data-quality summary)."
)
API_VERSION = "0.1.0"


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(health.router)

    return app


app = create_app()
