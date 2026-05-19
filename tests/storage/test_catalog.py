from __future__ import annotations

import json
from pathlib import Path

import pytest

from persephone.storage.catalog import DuplicateRunIdError, RunCatalog


def write_manifest(root: Path, run_id: str, status: str = "completed") -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": status,
                "config_snapshot": {
                    "name": f"{run_id} experiment",
                    "solvers": [{"plugin": "fake"}],
                },
                "config_hash": f"hash-{run_id}",
                "started_at": f"2026-01-0{len(run_id)}T00:00:00+00:00",
                "t_current": 3.0,
                "plugin_versions": {"fake": "0.1.0"},
            }
        ),
        encoding="utf-8",
    )
    return run_dir


def test_catalog_scans_run_manifests_and_filters_status(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    write_manifest(root, "completed-run", status="completed")
    write_manifest(root, "failed-run", status="failed")

    catalog = RunCatalog.scan(root)

    assert [run.run_id for run in catalog.list_runs()] == ["completed-run", "failed-run"]
    assert [run.run_id for run in catalog.list_runs(status="failed")] == ["failed-run"]
    summary = catalog.get("completed-run")
    assert summary.name == "completed-run experiment"
    assert summary.plugins == ["fake"]
    assert summary.path == root / "completed-run"


def test_catalog_get_accepts_existing_run_path(tmp_path: Path) -> None:
    run_dir = write_manifest(tmp_path / "runs", "path-run")

    summary = RunCatalog.scan(tmp_path / "runs").get(run_dir)

    assert summary.run_id == "path-run"


def test_catalog_rejects_duplicate_run_ids_across_roots(tmp_path: Path) -> None:
    write_manifest(tmp_path / "root-a", "same-run")
    write_manifest(tmp_path / "root-b", "same-run")

    with pytest.raises(DuplicateRunIdError):
        RunCatalog.scan([tmp_path / "root-a", tmp_path / "root-b"])
