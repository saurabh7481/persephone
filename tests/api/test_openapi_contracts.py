from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from persephone.api.app import create_app
from persephone.api.schemas import ApiError, FrameListResponse, RunSummaryResponse, SemanticManifest


def test_openapi_exposes_hardened_frame_contracts(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))

    openapi = client.get("/openapi.json").json()

    assert "/plugins/{plugin_name}/semantics" in openapi["paths"]
    assert "/runs/{run_id}/frames" in openapi["paths"]
    assert "/runs/{run_id}/frames/{frame_id}" in openapi["paths"]
    assert "/runs/{run_id}/frames/stream" in openapi["paths"]
    assert "/runs/{run_id}/explanations/run" in openapi["paths"]
    assert "/runs/{run_id}/frames/{frame_id}/explanation" in openapi["paths"]
    assert "/runs/{run_id}/selections/{selection_id}/explanation" in openapi["paths"]
    assert "ApiError" in openapi["components"]["schemas"]
    assert "ExplanationResponse" in openapi["components"]["schemas"]
    assert "FrameListResponse" in openapi["components"]["schemas"]
    assert "PluginSemanticsResponse" in openapi["components"]["schemas"]
    assert "RunSummaryResponse" in openapi["components"]["schemas"]


def test_schema_compatibility_for_critical_response_models() -> None:
    RunSummaryResponse.model_validate(
        {
            "run_id": "run-a",
            "name": "demo",
            "status": "completed",
            "started_at": "2026-05-21T00:00:00Z",
            "final_time": 1.0,
            "plugins": ["demo"],
            "config_hash": "abc",
            "artifact_path": "runs/run-a",
            "error_message": None,
            "cancel_requested": False,
        }
    )
    ApiError.model_validate(
        {
            "code": "frame_not_found",
            "message": "Frame not found",
            "details": {"frame_id": "missing"},
            "request_id": None,
        }
    )
    TypeAdapter(FrameListResponse).validate_python(
        {
            "metadata": {
                "run_id": "run-a",
                "frame_count": 1,
                "available_kinds": ["field"],
                "t_min": 0.1,
                "t_max": 0.1,
            },
            "frames": [
                {
                    "frame_id": "solver:field:1",
                    "kind": "field",
                    "t": 0.1,
                    "tick": 1,
                    "solver_id": "solver",
                    "source": "live",
                    "payload_ref": {"uri": "frames/frames.jsonl", "format": "jsonl"},
                }
            ],
        }
    )
    SemanticManifest.model_validate(
        {
            "entity_schemas": {
                "node": [
                    {
                        "name": "population",
                        "type": "number",
                        "label": "Population",
                        "required": True,
                    }
                ]
            },
            "state_schema": {
                "population": {
                    "name": "population",
                    "kind": "continuous",
                    "label": "Population",
                }
            },
            "metric_schema": {
                "population_sum": {
                    "name": "population_sum",
                    "kind": "scalar",
                    "label": "Population sum",
                }
            },
            "event_schema": {
                "population_changed": {
                    "name": "population_changed",
                    "label": "Population changed",
                }
            },
            "view_capabilities": [{"kind": "network", "default": True}],
            "explanation_capabilities": [{"scope": "run", "label": "Run summary"}],
            "preferred_view": "network",
        }
    )
