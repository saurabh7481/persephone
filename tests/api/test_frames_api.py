from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from persephone.api.app import create_app
from persephone.config.load import load_experiment_config


def heat_config_payload() -> dict[str, object]:
    config = load_experiment_config("configs/examples/heat_diffusion.yaml")
    config.scheduler.t_end = 0.2
    config.visualization.emit_every = 0.1
    return config.model_dump(mode="json")


def sir_config_payload() -> dict[str, object]:
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    config.scheduler.t_end = 2.0
    config.visualization.emit_every = 1.0
    return config.model_dump(mode="json")


def wait_for_terminal(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(80):
        response = client.get(f"/runs/{run_id}")
        response.raise_for_status()
        payload = response.json()
        if payload["status"] in {"completed", "failed", "cancelled"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"run did not finish: {run_id}")


def test_replay_frame_api_lists_and_loads_completed_heat_frames(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))
    started = client.post("/runs", json={"config": heat_config_payload(), "run_id": "heat-api"})
    assert started.status_code == 202
    assert wait_for_terminal(client, "heat-api")["status"] == "completed"

    listed = client.get("/runs/heat-api/frames", params={"kind": "field", "max_count": 1})
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["metadata"]["frame_count"] == 2
    assert payload["metadata"]["available_kinds"] == ["field"]
    assert payload["frames"][0]["kind"] == "field"

    frame_id = payload["frames"][0]["frame_id"]
    frame = client.get(f"/runs/heat-api/frames/{quote(frame_id, safe='')}")
    assert frame.status_code == 200
    assert frame.json()["values"]


def test_replay_frame_api_lists_sir_graph_frames(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))
    started = client.post("/runs", json={"config": sir_config_payload(), "run_id": "sir-api"})
    assert started.status_code == 202
    assert wait_for_terminal(client, "sir-api")["status"] == "completed"

    listed = client.get("/runs/sir-api/frames", params={"kind": "graph"})

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["metadata"]["available_kinds"] == ["graph"]
    assert payload["frames"][0]["kind"] == "graph"
    assert payload["frames"][0]["payload_ref"]["format"] == "jsonl"


def test_frame_stream_endpoint_streams_heat_frames_with_ids(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))
    started = client.post("/runs", json={"config": heat_config_payload(), "run_id": "frame-stream"})
    assert started.status_code == 202

    response = client.get("/runs/frame-stream/frames/stream", headers={"Last-Event-ID": "0"})

    assert response.status_code == 200
    assert "id: 1" in response.text
    assert "event: frame" in response.text
    assert "event: metric" in response.text
    assert "event: status" in response.text
    assert "completed" in response.text


def test_frame_api_returns_standard_error_for_missing_frame(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))
    started = client.post(
        "/runs", json={"config": heat_config_payload(), "run_id": "missing-frame"}
    )
    assert started.status_code == 202
    assert wait_for_terminal(client, "missing-frame")["status"] == "completed"

    response = client.get("/runs/missing-frame/frames/not-real")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "frame_not_found"
