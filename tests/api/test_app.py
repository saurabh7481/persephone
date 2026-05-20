from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from persephone.api.app import create_app
from persephone.config.load import load_experiment_config


def sir_config_payload() -> dict[str, object]:
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    return config.model_dump(mode="json")


def wait_for_completed(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(50):
        response = client.get(f"/runs/{run_id}")
        response.raise_for_status()
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"run did not finish: {run_id}")


def test_api_health_plugins_and_run_catalog(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))

    health = client.get("/health")
    plugins = client.get("/plugins")
    example = client.get("/examples/sir_epidemic")
    started = client.post("/runs", json={"config": sir_config_payload(), "run_id": "api-run"})

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert plugins.status_code == 200
    assert any(plugin["name"] == "sir_epidemic" for plugin in plugins.json())
    assert example.status_code == 200
    assert example.json()["solvers"][0]["plugin"] == "sir_epidemic"
    assert started.status_code == 202

    run = wait_for_completed(client, "api-run")
    assert run["status"] == "completed"

    runs = client.get("/runs")
    metrics = client.get("/runs/api-run/metrics", params={"metric": "infected_count"})
    events = client.get("/runs/api-run/events")

    assert any(item["run_id"] == "api-run" for item in runs.json())
    assert metrics.status_code == 200
    assert metrics.json()[0]["metric"] == "infected_count"
    assert events.status_code == 200


def test_api_allows_local_ui_cors_origin(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))

    response = client.get("/runs", headers={"Origin": "http://127.0.0.1:5173"})
    preflight = client.options(
        "/runs",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_stream_endpoint_returns_metric_events(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))
    started = client.post("/runs", json={"config": sir_config_payload(), "run_id": "stream-run"})
    assert started.status_code == 202
    wait_for_completed(client, "stream-run")

    response = client.get("/runs/stream-run/stream")

    assert response.status_code == 200
    assert "event: metric" in response.text
    assert "infected_count" in response.text


def test_failed_run_preserves_error_in_manifest(tmp_path: Path) -> None:
    payload = sir_config_payload()
    payload["solvers"] = [
        {
            **payload["solvers"][0],  # type: ignore[index]
            "params": {
                **payload["solvers"][0]["params"],  # type: ignore[index]
                "contact_graph": str(tmp_path / "missing.csv"),
            },
        }
    ]
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))

    response = client.post("/runs", json={"config": payload, "run_id": "failed-api-run"})

    assert response.status_code == 202
    run = wait_for_completed(client, "failed-api-run")
    assert run["status"] == "failed"
    manifest_path = tmp_path / "runs" / "failed-api-run" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert "missing.csv" in manifest["error_message"]


def test_run_manager_tracks_active_status_transitions(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))

    response = client.post("/runs", json={"config": sir_config_payload(), "run_id": "active-run"})

    assert response.status_code == 202
    assert response.json()["status"] in {"pending", "running", "completed"}
    run = wait_for_completed(client, "active-run")
    assert run["status"] == "completed"
    manifest = json.loads((tmp_path / "runs" / "active-run" / "manifest.json").read_text())
    assert manifest["status"] == "completed"


def test_api_creates_parameter_sweep_and_links_children(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))

    response = client.post(
        "/sweeps",
        json={
            "sweep_id": "api-sweep",
            "name": "API sweep",
            "base_config": sir_config_payload(),
            "parameter": "solvers[0].params.p_infect",
            "values": [0.2, 0.4],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["sweep_id"] == "api-sweep"
    assert [child["run_id"] for child in payload["child_runs"]] == [
        "api-sweep-001",
        "api-sweep-002",
    ]
    child_manifest = json.loads(
        (tmp_path / "runs" / "api-sweep-001" / "manifest.json").read_text(encoding="utf-8")
    )
    assert child_manifest["sweep_id"] == "api-sweep"


def test_api_compares_two_runs_by_metric(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))
    for run_id in ["compare-a", "compare-b"]:
        started = client.post("/runs", json={"config": sir_config_payload(), "run_id": run_id})
        assert started.status_code == 202
        wait_for_completed(client, run_id)

    response = client.get(
        "/compare",
        params={"run": ["compare-a", "compare-b"], "metric": "infected_count"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metric"] == "infected_count"
    assert payload["run_a"] == "compare-a"
    assert payload["run_b"] == "compare-b"
    assert payload["aligned"][0]["t"] >= 0
    assert payload["summaries"]["compare-a"]["peak"] >= 0
