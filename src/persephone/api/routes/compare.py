from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, HTTPException, Query, Request

from persephone.api.manager import RunManager
from persephone.compare import compare_metric_records
from persephone.storage.catalog import RunCatalogError

router = APIRouter()


@router.get("/compare")
def compare_runs(
    request: Request,
    run: Annotated[list[str], Query(min_length=2, max_length=2)],
    metric: str,
) -> dict[str, Any]:
    manager = cast(RunManager, request.app.state.run_manager)
    run_a, run_b = run
    try:
        result = compare_metric_records(
            run_a=run_a,
            run_b=run_b,
            metric=metric,
            records_a=manager.metric_records(run_a, metric=metric),
            records_b=manager.metric_records(run_b, metric=metric),
        )
    except RunCatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result.model_dump(mode="json")
