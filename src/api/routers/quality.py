"""Data-quality summary endpoint backed by the Bronze raw tables."""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_repository
from src.api.repositories.base import IspuRepository
from src.api.schemas.quality import QualitySummaryRow

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/summary", response_model=list[QualitySummaryRow])
def summary(
    repo: IspuRepository = Depends(get_repository),
) -> list[QualitySummaryRow]:
    """Per-source-file valid vs quarantined counts and the dominant reason.

    Surfaces the pipeline's "zero silent drops" guarantee: every ingested row
    is either valid or quarantined with an explicit reason.
    """
    return repo.get_quality_summary()
