from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from persephone.api.manager import RunManager, serialize_run
from persephone.api.schemas import RunCreateRequest
from persephone.storage.catalog import RunCatalogError

router = APIRouter()


@router.post("/runs", status_code=202)
def start_run(payload: RunCreateRequest, request: Request) -> dict[str, Any]:
    managed = _manager(request).start(payload.config, run_id=payload.run_id)
    return serialize_run(managed)


@router.get("/runs")
def list_runs(
    request: Request,
    status: Annotated[
        str | None, Query(pattern="^(completed|failed|running|pending|cancelling|cancelled)$")
    ] = None,
) -> list[dict[str, Any]]:
    return [serialize_run(run) for run in _manager(request).list_runs(status=status)]


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request) -> dict[str, Any]:
    try:
        return serialize_run(_manager(request).get(run_id))
    except RunCatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/metrics")
def get_metrics(
    run_id: str,
    request: Request,
    metric: str | None = None,
) -> list[dict[str, Any]]:
    try:
        return _manager(request).metric_records(run_id, metric=metric)
    except RunCatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/events")
def get_events(run_id: str, request: Request) -> list[dict[str, Any]]:
    try:
        return _manager(request).event_records(run_id)
    except RunCatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/stream")
def stream_run(run_id: str, request: Request) -> StreamingResponse:
    manager = _manager(request)
    try:
        manager.get(run_id)
    except RunCatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(
        manager.sse_metric_events(run_id),
        media_type="text/event-stream",
    )


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, request: Request) -> dict[str, Any]:
    try:
        return serialize_run(_manager(request).request_cancel(run_id))
    except RunCatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _manager(request: Request) -> RunManager:
    return cast(RunManager, request.app.state.run_manager)
