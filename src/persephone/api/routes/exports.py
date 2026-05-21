from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, cast

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from persephone.export import export_run_archive
from persephone.fields import export_field_artifact, field_to_dict, list_field_artifacts
from persephone.storage.catalog import RunCatalogError

router = APIRouter()


@router.get("/runs/{run_id}/export")
def export_run_endpoint(
    run_id: str,
    request: Request,
    format: Annotated[Literal["csv", "parquet"], Query()] = "csv",
) -> FileResponse:
    try:
        archive = export_run_archive(request.app.state.artifact_root, run_id, export_format=format)
    except (RunCatalogError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=f"{run_id}-{format}.zip",
    )


@router.get("/runs/{run_id}/fields")
def list_fields(run_id: str, request: Request) -> list[dict[str, object]]:
    try:
        return [
            field_to_dict(field) for field in list_field_artifacts(_artifact_root(request), run_id)
        ]
    except (RunCatalogError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/fields/{field_id:path}", response_model=None)
def download_field(
    run_id: str,
    field_id: str,
    request: Request,
    format: Annotated[Literal["csv", "npy"], Query()] = "csv",
) -> Response:
    try:
        suffix = "csv" if format == "csv" else "npy"
        output = request.app.state.artifact_root / run_id / "exports" / f"field.{suffix}"
        path = export_field_artifact(
            _artifact_root(request),
            run_id,
            field_id,
            output=output,
            export_format=format,
        )
    except (RunCatalogError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if format == "csv":
        return Response(path.read_text(encoding="utf-8"), media_type="text/csv")
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)


def _artifact_root(request: Request) -> Path:
    return cast(Path, request.app.state.artifact_root)
