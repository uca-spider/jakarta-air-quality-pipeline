"""Meta endpoints: reference data for API consumers."""

from fastapi import APIRouter

from src.api.services.ispu_categories import ISPU_BANDS, Band

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/categories", response_model=list[Band])
def categories() -> list[Band]:
    """Return the ISPU category bands and their numeric index ranges."""
    return ISPU_BANDS
