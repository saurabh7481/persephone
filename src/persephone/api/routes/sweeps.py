from __future__ import annotations

from pathlib import Path
from typing import cast

from fastapi import APIRouter, Request

from persephone.api.schemas import SweepCreateRequest
from persephone.sweeps import SweepManifest, execute_sweep

router = APIRouter()


@router.post("/sweeps", status_code=201, response_model=SweepManifest)
def start_sweep(payload: SweepCreateRequest, request: Request) -> dict[str, object]:
    artifact_root = cast(Path, request.app.state.artifact_root)
    manifest = execute_sweep(payload.to_sweep_config(), artifact_root=artifact_root)
    return manifest.model_dump(mode="json")
