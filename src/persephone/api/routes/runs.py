from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any, cast

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from persephone.api.manager import RunManager, serialize_run
from persephone.api.schemas import (
    ApiError,
    EventRecordResponse,
    ExplanationResponse,
    MetricRecordResponse,
    PluginSemanticsResponse,
    RunCreateRequest,
    RunSummaryResponse,
    SemanticManifest,
)
from persephone.core.interpretation import InterpretationService
from persephone.registry.registry import PluginNotFoundError, PluginRegistry
from persephone.storage.catalog import RunCatalogError

router = APIRouter()


@router.post(
    "/runs",
    status_code=202,
    response_model=RunSummaryResponse,
    responses={404: {"model": ApiError}},
)
def start_run(payload: RunCreateRequest, request: Request) -> dict[str, Any]:
    managed = _manager(request).start(payload.config, run_id=payload.run_id)
    return serialize_run(managed)


@router.get("/runs", response_model=list[RunSummaryResponse])
def list_runs(
    request: Request,
    status: Annotated[
        str | None, Query(pattern="^(completed|failed|running|pending|cancelling|cancelled)$")
    ] = None,
) -> list[dict[str, Any]]:
    return [_serialize_run_with_semantics(serialize_run(run), request) for run in _manager(request).list_runs(status=status)]


@router.get(
    "/runs/{run_id}", response_model=RunSummaryResponse, responses={404: {"model": ApiError}}
)
def get_run(run_id: str, request: Request) -> dict[str, Any]:
    try:
        return _serialize_run_with_semantics(serialize_run(_manager(request).get(run_id)), request)
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc


@router.get(
    "/runs/{run_id}/metrics",
    response_model=list[MetricRecordResponse],
    responses={404: {"model": ApiError}},
)
def get_metrics(
    run_id: str,
    request: Request,
    metric: str | None = None,
) -> list[dict[str, Any]]:
    try:
        return _manager(request).metric_records(run_id, metric=metric)
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc


@router.get(
    "/runs/{run_id}/events",
    response_model=list[EventRecordResponse],
    responses={404: {"model": ApiError}},
)
def get_events(run_id: str, request: Request) -> list[dict[str, Any]]:
    try:
        return _manager(request).event_records(run_id)
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc


@router.get(
    "/runs/{run_id}/explanations/run",
    response_model=ExplanationResponse,
    responses={404: {"model": ApiError}},
)
def get_run_explanation(run_id: str, request: Request) -> dict[str, Any]:
    return _explanation_response(run_id, request, scope="run")


@router.get(
    "/runs/{run_id}/frames/{frame_id}/explanation",
    response_model=ExplanationResponse,
    responses={404: {"model": ApiError}},
)
def get_frame_explanation(run_id: str, frame_id: str, request: Request) -> dict[str, Any]:
    return _explanation_response(run_id, request, scope="frame", frame_id=frame_id)


@router.get(
    "/runs/{run_id}/selections/{selection_id}/explanation",
    response_model=ExplanationResponse,
    responses={404: {"model": ApiError}},
)
def get_selection_explanation(run_id: str, selection_id: str, request: Request) -> dict[str, Any]:
    return _explanation_response(run_id, request, scope="selection", selection_id=selection_id)


@router.get("/runs/{run_id}/stream", responses={404: {"model": ApiError}})
def stream_run(run_id: str, request: Request) -> StreamingResponse:
    manager = _manager(request)
    try:
        manager.get(run_id)
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc
    return StreamingResponse(
        manager.sse_metric_events(run_id),
        media_type="text/event-stream",
    )


@router.post(
    "/runs/{run_id}/cancel",
    response_model=RunSummaryResponse,
    responses={404: {"model": ApiError}},
)
def cancel_run(run_id: str, request: Request) -> dict[str, Any]:
    try:
        return serialize_run(_manager(request).request_cancel(run_id))
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc


def _manager(request: Request) -> RunManager:
    return cast(RunManager, request.app.state.run_manager)


def _registry(request: Request) -> PluginRegistry:
    return cast(PluginRegistry, request.app.state.plugin_registry)


def _interpretation_service(request: Request) -> InterpretationService:
    return cast(InterpretationService, request.app.state.interpretation_service)


def _serialize_run_with_semantics(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    payload["plugin_semantics"] = _plugin_semantics(payload.get("plugins", []), request)
    return payload


def _plugin_semantics(plugin_names: list[str], request: Request) -> list[dict[str, Any]]:
    registry = _registry(request)
    registry.discover()
    semantics: list[dict[str, Any]] = []
    for plugin_name in plugin_names:
        try:
            manifest = registry.get(plugin_name)
        except PluginNotFoundError:
            continue
        semantics.append(
            PluginSemanticsResponse(
                name=manifest.name,
                version=manifest.version,
                semantics=SemanticManifest.model_validate(asdict(manifest.semantics)),
            ).model_dump(mode="json")
        )
    return semantics


def _explanation_response(
    run_id: str,
    request: Request,
    *,
    scope: str,
    frame_id: str | None = None,
    selection_id: str | None = None,
) -> dict[str, Any]:
    try:
        run = _manager(request).get(run_id)
        packets = _manager(request).explanation_packets(run_id)
        context = _manager(request).run_context(run_id)
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc

    service = _interpretation_service(request)
    try:
        if scope == "run":
            interpretation = service.interpret_run(
                context=context,
                packets=packets,
                completed=getattr(run, "status", "") == "completed",
            )
        elif scope == "frame" and frame_id is not None:
            interpretation = service.interpret_frame(
                context=context,
                packets=packets,
                frame_id=frame_id,
                completed=getattr(run, "status", "") == "completed",
            )
        elif scope == "selection" and selection_id is not None:
            interpretation = service.interpret_selection(
                context=context,
                packets=packets,
                selection_id=selection_id,
                completed=getattr(run, "status", "") == "completed",
            )
        else:
            raise ValueError("Unsupported explanation scope")
    except ValueError:
        return ExplanationResponse(
            run_id=run_id,
            scope=scope,
            frame_id=frame_id,
            selection_id=selection_id,
            available=False,
            reason="No explanation facts available for the requested scope.",
            interpretation=None,
        ).model_dump(mode="json")

    return ExplanationResponse(
        run_id=run_id,
        scope=scope,
        frame_id=frame_id,
        selection_id=selection_id,
        available=True,
        reason=None,
        interpretation=interpretation,
    ).model_dump(mode="json")


def _not_found(code: str, message: str, details: dict[str, Any]) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ApiError(code=code, message=message, details=details).model_dump(mode="json"),
    )
