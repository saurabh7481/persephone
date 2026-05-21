from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import pyarrow as pa
import pyarrow.parquet as pq

from persephone.storage.catalog import RunCatalog

ExportFormat = Literal["csv", "parquet"]
RecordType = Literal["metrics", "events"]


@dataclass(frozen=True)
class ExportedFile:
    record_type: RecordType
    path: Path
    row_count: int


@dataclass(frozen=True)
class ExportManifest:
    run_id: str
    export_format: ExportFormat
    files: list[ExportedFile]


def export_run(
    artifact_root: str | Path,
    run_id: str,
    *,
    output_dir: str | Path,
    export_format: ExportFormat,
) -> ExportManifest:
    run_dir = RunCatalog.scan(artifact_root).get(run_id).path
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    files = [
        _export_records(run_dir, output, "metrics", export_format),
        _export_records(run_dir, output, "events", export_format),
    ]
    return ExportManifest(run_id=run_id, export_format=export_format, files=files)


def export_run_archive(
    artifact_root: str | Path,
    run_id: str,
    *,
    export_format: ExportFormat,
) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"persephone-export-{run_id}-"))
    manifest = export_run(
        artifact_root,
        run_id,
        output_dir=temp_dir / "records",
        export_format=export_format,
    )
    archive_path = temp_dir / f"{run_id}-{export_format}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for exported in manifest.files:
            archive.write(exported.path, arcname=exported.path.name)
    return archive_path


def _export_records(
    run_dir: Path,
    output: Path,
    record_type: RecordType,
    export_format: ExportFormat,
) -> ExportedFile:
    records = [_flatten_record(record) for record in _read_jsonl(run_dir / f"{record_type}.jsonl")]
    if export_format == "csv":
        path = output / f"{record_type}.csv"
        _write_csv(path, records)
    elif export_format == "parquet":
        path = output / f"{record_type}.parquet"
        _write_parquet(path, records)
    else:
        raise ValueError(f"Unsupported export format: {export_format}")
    return ExportedFile(record_type=record_type, path=path, row_count=len(records))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    flattened = dict(record)
    tags = flattened.get("tags")
    if isinstance(tags, dict):
        flattened["tags"] = json.dumps(tags, sort_keys=True)
    return flattened


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for record in records for key in record}) or [
        "run_id",
        "solver_id",
        "t",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def _write_parquet(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(records) if records else pa.table({})
    pq.write_table(table, path)  # type: ignore[no-untyped-call]
