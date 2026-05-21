from __future__ import annotations

from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from persephone.api.manager import RunManager
from persephone.api.schemas import ApiError, FrameListResponse
from persephone.frames import FrameNotFoundError, get_frame, list_frames
from persephone.storage.catalog import RunCatalogError

router = APIRouter()


@router.get(
    "/runs/{run_id}/frames/stream",
    responses={404: {"model": ApiError}},
)
def stream_frames(
    run_id: str,
    request: Request,
    last_event_id: Annotated[str | None, Query(alias="last_event_id")] = None,
) -> StreamingResponse:
    manager = _manager(request)
    try:
        manager.get(run_id)
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc
    header_last_event_id = request.headers.get("last-event-id")
    return StreamingResponse(
        manager.sse_frame_events(run_id, last_event_id=last_event_id or header_last_event_id),
        media_type="text/event-stream",
    )


@router.get(
    "/runs/{run_id}/frames",
    response_model=FrameListResponse,
    responses={404: {"model": ApiError}},
)
def list_run_frames(
    run_id: str,
    request: Request,
    kind: Literal["field", "graph"] | None = None,
    t_min: float | None = None,
    t_max: float | None = None,
    solver_id: str | None = None,
    max_count: Annotated[int | None, Query(gt=0, le=10_000)] = None,
) -> FrameListResponse:
    try:
        return list_frames(
            request.app.state.artifact_root,
            run_id,
            kind=kind,
            t_min=t_min,
            t_max=t_max,
            solver_id=solver_id,
            max_count=max_count,
        )
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc


@router.get(
    "/runs/{run_id}/frames/{frame_id:path}",
    response_model=dict[str, Any],
    responses={404: {"model": ApiError}},
)
def get_run_frame(run_id: str, frame_id: str, request: Request) -> dict[str, Any]:
    try:
        return get_frame(request.app.state.artifact_root, run_id, frame_id)
    except RunCatalogError as exc:
        raise _not_found("run_not_found", str(exc), {"run_id": run_id}) from exc
    except FrameNotFoundError as exc:
        raise _not_found(
            "frame_not_found",
            str(exc),
            {"run_id": run_id, "frame_id": frame_id},
        ) from exc


def _manager(request: Request) -> RunManager:
    return cast(RunManager, request.app.state.run_manager)


def _not_found(code: str, message: str, details: dict[str, Any]) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ApiError(code=code, message=message, details=details).model_dump(mode="json"),
    )
