from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import numpy as np

from persephone.core.records import EventRecord, MetricRecord
from persephone.storage.errors import UnsupportedStateValueError


class JsonlMetricSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write(self, records: list[dict[str, Any]]) -> None:
        validated = MetricRecord.validate_many(records)
        ordered = sorted(validated, key=lambda record: (record.t, record.metric, record.solver_id))
        _append_jsonl(self.path, [record.model_dump(mode="json") for record in ordered])


class JsonlEventSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write(self, records: list[dict[str, Any]]) -> None:
        validated = EventRecord.validate_many(records)
        ordered = sorted(validated, key=lambda record: (record.t, record.event, record.solver_id))
        _append_jsonl(self.path, [record.model_dump(mode="json") for record in ordered])


class NpzStateSink:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write_state(self, run_id: str, state: Mapping[str, object]) -> None:
        run_dir = self.root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        write_state_npz(run_dir / "final_state.npz", run_dir / "final_state.json", state)


def write_state_npz(
    array_path: str | Path,
    metadata_path: str | Path,
    state: Mapping[str, object],
) -> None:
    arrays = _validated_arrays(state)
    np.savez(array_path, **cast(dict[str, Any], arrays))
    metadata = {
        key: {"kind": "ndarray", "shape": list(value.shape), "dtype": str(value.dtype)}
        for key, value in arrays.items()
    }
    _write_json_atomic(Path(metadata_path), metadata)


def _validated_arrays(state: Mapping[str, object]) -> dict[str, np.ndarray[Any, Any]]:
    arrays: dict[str, np.ndarray[Any, Any]] = {}
    for key, value in state.items():
        if isinstance(value, np.ma.MaskedArray):
            raise UnsupportedStateValueError(
                f"State value '{key}' uses MaskedArray, which is not supported yet"
            )
        if _is_sparse_matrix(value):
            raise UnsupportedStateValueError(
                f"State value '{key}' uses a sparse matrix, which is not supported yet"
            )
        if not isinstance(value, np.ndarray):
            raise UnsupportedStateValueError(
                f"State value '{key}' must be a NumPy ndarray, got {type(value).__name__}"
            )
        arrays[key] = value
    return arrays


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def _is_sparse_matrix(value: object) -> bool:
    return hasattr(value, "tocoo") and hasattr(value, "shape") and hasattr(value, "dtype")
