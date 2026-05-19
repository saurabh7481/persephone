from __future__ import annotations

from fastapi import APIRouter

from persephone.registry.registry import PluginRegistry

router = APIRouter()


@router.get("/plugins")
def plugins() -> list[dict[str, str]]:
    registry = PluginRegistry()
    registry.discover()
    return registry.list_all()
