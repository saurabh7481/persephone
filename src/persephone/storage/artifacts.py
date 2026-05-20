from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from persephone.core.run import RunContext
from persephone.storage.errors import StorageError, UnsupportedStateValueError
from persephone.storage.sinks import JsonlEventSink, JsonlMetricSink, write_state_npz


class ArtifactStore:
    def __init__(self, root: str | Path = "runs") -> None:
        self.root = Path(root)
        self._contexts: dict[str, RunContext] = {}

    def initialize_run(self, context: RunContext) -> Path:
        run_dir = self.run_dir(context.run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        self._contexts[context.run_id] = context
        self._write_manifest(context)
        (run_dir / "metrics.jsonl").touch()
        (run_dir / "events.jsonl").touch()
        return run_dir

    def run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def update_status(
        self,
        run_id: str,
        status: str,
        t_current: float | None = None,
        error_message: str | None = None,
    ) -> None:
        context = self._contexts[run_id]
        context.mark_status(status=status, t_current=t_current, error_message=error_message)
        self._write_manifest(context)

    def write_metrics(self, run_id: str, metrics: list[dict[str, Any]]) -> None:
        for metric in metrics:
            metric.setdefault("run_id", run_id)
            metric.setdefault("solver_id", "unknown")
            metric.setdefault("tags", {})
        JsonlMetricSink(self.run_dir(run_id) / "metrics.jsonl").write(metrics)

    def write_events(self, run_id: str, events: list[dict[str, Any]]) -> None:
        for event in events:
            event.setdefault("run_id", run_id)
            event.setdefault("solver_id", "unknown")
            event.setdefault("event", event.get("event_type", "event"))
            event.setdefault("tags", {})
        JsonlEventSink(self.run_dir(run_id) / "events.jsonl").write(events)

    def write_final_state(self, run_id: str, state: Mapping[str, object]) -> None:
        run_dir = self.run_dir(run_id)
        write_state_npz(run_dir / "final_state.npz", run_dir / "final_state.json", state)

    def write_checkpoint(
        self,
        run_id: str,
        *,
        tick: int,
        logical_time: float,
        state: dict[str, NDArray[np.generic]],
        bus_snapshot: dict[str, Any],
        rng_states: dict[str, Any],
    ) -> Path:
        checkpoint_dir = self.run_dir(run_id) / "checkpoints" / f"{tick:06d}"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        write_state_npz(checkpoint_dir / "state.npz", checkpoint_dir / "state.json", state)
        self._write_json(checkpoint_dir / "bus.json", bus_snapshot)
        self._write_json(checkpoint_dir / "rng.json", rng_states)
        manifest = self._contexts[run_id]
        self._write_json(
            checkpoint_dir / "checkpoint.json",
            {
                "schema_version": 1,
                "run_id": run_id,
                "tick": tick,
                "logical_time": logical_time,
                "engine_version": manifest.engine_version,
                "sdk_version": manifest.sdk_version,
                "plugin_versions": manifest.plugin_versions,
                "config_hash": manifest.config_hash,
            },
        )
        return checkpoint_dir

    def _write_manifest(self, context: RunContext) -> None:
        self._write_json(self.run_dir(context.run_id) / "manifest.json", context.to_manifest())

    def _write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(_json_safe(value), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temp_path.replace(path)


def _json_safe(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    return value


__all__ = ["ArtifactStore", "StorageError", "UnsupportedStateValueError"]
