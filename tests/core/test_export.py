from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pyarrow.parquet as pq

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine
from persephone.export import export_run, export_run_archive


def test_export_run_writes_csv_and_parquet_for_metrics_and_events(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(config, run_id="export-run")
    assert result.status == "completed"

    csv_manifest = export_run(
        tmp_path / "runs",
        "export-run",
        output_dir=tmp_path / "csv-export",
        export_format="csv",
    )
    parquet_manifest = export_run(
        tmp_path / "runs",
        "export-run",
        output_dir=tmp_path / "parquet-export",
        export_format="parquet",
    )

    assert {item.record_type for item in csv_manifest.files} == {"metrics", "events"}
    assert {item.record_type for item in parquet_manifest.files} == {"metrics", "events"}

    metrics_jsonl = [
        json.loads(line)
        for line in (tmp_path / "runs" / "export-run" / "metrics.jsonl").read_text().splitlines()
        if line.strip()
    ]
    with (tmp_path / "csv-export" / "metrics.csv").open(newline="", encoding="utf-8") as handle:
        metrics_csv = list(csv.DictReader(handle))
    assert len(metrics_csv) == len(metrics_jsonl)
    assert {row["metric"] for row in metrics_csv} >= {"infected_count", "scheduler.wall_time_ms"}

    metrics_table = pq.read_table(tmp_path / "parquet-export" / "metrics.parquet")
    assert metrics_table.num_rows == len(metrics_jsonl)
    assert set(metrics_table.column_names) >= {"run_id", "solver_id", "metric", "value", "t"}


def test_export_run_archive_contains_both_record_files(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(config, run_id="archive-run")
    assert result.status == "completed"

    archive = export_run_archive(tmp_path / "runs", "archive-run", export_format="csv")

    with zipfile.ZipFile(archive) as handle:
        assert sorted(handle.namelist()) == ["events.csv", "metrics.csv"]
