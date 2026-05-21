from __future__ import annotations

from fastapi import APIRouter

from persephone.api.schemas import PluginSummaryResponse
from persephone.registry.registry import PluginRegistry

router = APIRouter()


@router.get("/plugins", response_model=list[PluginSummaryResponse])
def plugins() -> list[dict[str, str]]:
    registry = PluginRegistry()
    registry.discover()
    return registry.list_all()
