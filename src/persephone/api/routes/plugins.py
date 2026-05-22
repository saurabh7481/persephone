from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request

from persephone.api.schemas import (
    ApiError,
    PluginSemanticsResponse,
    PluginSummaryResponse,
    SemanticManifest,
)
from persephone.registry.registry import PluginNotFoundError, PluginRegistry

router = APIRouter()


@router.get("/plugins", response_model=list[PluginSummaryResponse])
def plugins(request: Request) -> list[dict[str, str]]:
    registry = _registry(request)
    registry.discover()
    return registry.list_all()


@router.get(
    "/plugins/{plugin_name}/semantics",
    response_model=PluginSemanticsResponse,
    responses={404: {"model": ApiError}},
)
def plugin_semantics(plugin_name: str, request: Request) -> dict[str, Any]:
    registry = _registry(request)
    registry.discover()
    try:
        manifest = registry.get(plugin_name)
    except PluginNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="plugin_not_found",
                message=str(exc),
                details={"plugin_name": plugin_name},
            ).model_dump(mode="json"),
        ) from exc

    return _manifest_semantics_payload(manifest.name, manifest.version, manifest.semantics)


def _registry(request: Request) -> PluginRegistry:
    return cast(PluginRegistry, request.app.state.plugin_registry)


def _manifest_semantics_payload(name: str, version: str, semantics: object) -> dict[str, Any]:
    return {
        "name": name,
        "version": version,
        "semantics": SemanticManifest.model_validate(asdict(semantics)).model_dump(mode="json"),
    }
