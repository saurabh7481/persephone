from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from persephone.api.manager import RunManager, serialize_run
from persephone.api.schemas import (
    ApiError,
    EventRecordResponse,
    MetricRecordResponse,
    RunCreateRequest,
    RunSummaryResponse,
)
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
    return [serialize_run(run) for run in _manager(request).list_runs(status=status)]


@router.get(
    "/runs/{run_id}", response_model=RunSummaryResponse, responses={404: {"model": ApiError}}
)
def get_run(run_id: str, request: Request) -> dict[str, Any]:
    try:
        return serialize_run(_manager(request).get(run_id))
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


def _not_found(code: str, message: str, details: dict[str, Any]) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ApiError(code=code, message=message, details=details).model_dump(mode="json"),
    )
