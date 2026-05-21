from __future__ import annotations

import time
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from persephone.api.app import create_app
from persephone.config.load import load_experiment_config


def _payload(path: str) -> dict[str, object]:
    return load_experiment_config(path).model_dump(mode="json")


def _wait(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(50):
        response = client.get(f"/runs/{run_id}")
        response.raise_for_status()
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"run did not finish: {run_id}")


def test_api_downloads_csv_and_parquet_export_archives(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))
    response = client.post(
        "/runs",
        json={"run_id": "api-export", "config": _payload("configs/examples/sir_epidemic.yaml")},
    )
    assert response.status_code == 202
    assert _wait(client, "api-export")["status"] == "completed"

    csv_response = client.get("/runs/api-export/export", params={"format": "csv"})
    parquet_response = client.get("/runs/api-export/export", params={"format": "parquet"})

    assert csv_response.status_code == 200
    assert parquet_response.status_code == 200
    with zipfile.ZipFile(BytesIO(csv_response.content)) as archive:
        assert sorted(archive.namelist()) == ["events.csv", "metrics.csv"]
    with zipfile.ZipFile(BytesIO(parquet_response.content)) as archive:
        assert sorted(archive.namelist()) == ["events.parquet", "metrics.parquet"]


def test_api_lists_and_downloads_field_artifacts(tmp_path: Path) -> None:
    client = TestClient(create_app(artifact_root=tmp_path / "runs"))
    response = client.post(
        "/runs",
        json={"run_id": "api-field", "config": _payload("configs/examples/heat_diffusion.yaml")},
    )
    assert response.status_code == 202
    assert _wait(client, "api-field")["status"] == "completed"

    fields = client.get("/runs/api-field/fields")
    assert fields.status_code == 200
    field_id = fields.json()[0]["id"]

    download = client.get(f"/runs/api-field/fields/{field_id}", params={"format": "csv"})
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("text/csv")
    assert b"," in download.content
