from __future__ import annotations

import json
from pathlib import Path

from persephone.config.load import load_experiment_config
from persephone.runtime import PythonSimulationRuntime


def test_python_runtime_runs_existing_engine_and_records_backend_metadata(tmp_path: Path) -> None:
    runtime = PythonSimulationRuntime(artifact_root=tmp_path / "runs")
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")

    result = runtime.start_run(config, run_id="runtime-run")

    assert result.status == "completed"
    capabilities = runtime.runtime_capabilities()
    assert capabilities.backend == "python"
    assert capabilities.supports_replay is True

    manifest = json.loads(
        (tmp_path / "runs" / "runtime-run" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["runtime_backend"] == "python"
    assert manifest["runtime_version"]


def test_python_runtime_stream_records_reads_persisted_metric_and_event_records(
    tmp_path: Path,
) -> None:
    runtime = PythonSimulationRuntime(artifact_root=tmp_path / "runs")
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    runtime.start_run(config, run_id="stream-records")

    records = list(runtime.stream_records("stream-records"))

    assert any(kind == "metric" for kind, _record in records)
    assert any(record.get("run_id") == "stream-records" for _kind, record in records)
