from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import quote, unquote

import numpy as np

from persephone.storage.catalog import RunCatalog

FieldExportFormat = Literal["csv", "npy"]


@dataclass(frozen=True)
class FieldArtifact:
    id: str
    name: str
    source: str
    path: Path
    dimensions: list[int]
    dtype: str
    bounds: dict[str, float]
    units: str
    visualization: dict[str, Any]
    tick: int | None = None


def list_field_artifacts(artifact_root: str | Path, run_id: str) -> list[FieldArtifact]:
    run_dir = RunCatalog.scan(artifact_root).get(run_id).path
    fields: list[FieldArtifact] = []
    fields.extend(_fields_from_npz(run_dir / "final_state.npz", source="final_state"))
    for checkpoint_dir in sorted((run_dir / "checkpoints").glob("*")):
        if not checkpoint_dir.is_dir():
            continue
        tick = int(checkpoint_dir.name)
        fields.extend(
            _fields_from_npz(
                checkpoint_dir / "state.npz",
                source="checkpoint",
                tick=tick,
            )
        )
    return fields


def export_field_artifact(
    artifact_root: str | Path,
    run_id: str,
    field_id: str,
    *,
    output: str | Path,
    export_format: FieldExportFormat = "csv",
) -> Path:
    field = _find_field(artifact_root, run_id, field_id)
    array = _load_array(field)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "csv":
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(array.tolist())
    elif export_format == "npy":
        np.save(output_path, array)
    else:
        raise ValueError(f"Unsupported field export format: {export_format}")
    return output_path


def field_to_dict(field: FieldArtifact) -> dict[str, Any]:
    return {
        "id": quote(field.id, safe=":.-_"),
        "raw_id": field.id,
        "name": field.name,
        "source": field.source,
        "dimensions": field.dimensions,
        "dtype": field.dtype,
        "bounds": field.bounds,
        "units": field.units,
        "visualization": field.visualization,
        "tick": field.tick,
    }


def _fields_from_npz(path: Path, *, source: str, tick: int | None = None) -> list[FieldArtifact]:
    if not path.exists():
        return []
    fields: list[FieldArtifact] = []
    with np.load(path) as data:
        for name in sorted(data.files):
            array = data[name]
            if array.ndim != 2:
                continue
            source_prefix = source if tick is None else f"{source}:{tick:06d}"
            fields.append(
                FieldArtifact(
                    id=f"{source_prefix}:{name}",
                    name=name,
                    source=source,
                    path=path,
                    dimensions=[int(array.shape[0]), int(array.shape[1])],
                    dtype=str(array.dtype),
                    bounds={"min": float(np.min(array)), "max": float(np.max(array))},
                    units=_units_for_name(name),
                    visualization={"kind": "heatmap", "color_scale": "viridis"},
                    tick=tick,
                )
            )
    return fields


def _find_field(artifact_root: str | Path, run_id: str, field_id: str) -> FieldArtifact:
    decoded_id = unquote(field_id)
    for field in list_field_artifacts(artifact_root, run_id):
        if field.id == decoded_id or quote(field.id, safe=":.-_") == field_id:
            return field
    raise ValueError(f"Field artifact not found: {field_id}")


def _load_array(field: FieldArtifact) -> np.ndarray[Any, Any]:
    with np.load(field.path) as data:
        return cast(np.ndarray[Any, Any], data[field.name])


def _units_for_name(name: str) -> str:
    if name.endswith("temperature"):
        return "temperature"
    metadata_path = Path(str(name))
    metadata = metadata_path.name
    return metadata or "unitless"


def write_field_metadata(artifact_root: str | Path, run_id: str) -> Path:
    run_dir = RunCatalog.scan(artifact_root).get(run_id).path
    path = run_dir / "fields.json"
    path.write_text(
        json.dumps([field_to_dict(field) for field in list_field_artifacts(artifact_root, run_id)]),
        encoding="utf-8",
    )
    return path
