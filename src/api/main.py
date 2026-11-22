"""FastAPI application factory for the Jakarta Air Quality REST API."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.config import get_settings
from src.api.repositories.base import RepositoryError
from src.api.routers import health, measurements, meta, stations, trends

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

    @app.exception_handler(RepositoryError)
    async def _repository_error_handler(
        request: Request, exc: RepositoryError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"detail": "Data source unavailable."}
        )

    app.include_router(health.router)
    app.include_router(meta.router)
    app.include_router(stations.router)
    app.include_router(measurements.router)
    app.include_router(trends.router)

    return app


app = create_app()
