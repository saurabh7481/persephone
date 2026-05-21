from __future__ import annotations

from fastapi import APIRouter

from persephone import __version__
from persephone.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
