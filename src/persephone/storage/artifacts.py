from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from persephone.core.run import RunContext


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
        self._append_jsonl(self.run_dir(run_id) / "metrics.jsonl", metrics)

    def write_events(self, run_id: str, events: list[dict[str, Any]]) -> None:
        self._append_jsonl(self.run_dir(run_id) / "events.jsonl", events)

    def write_final_state(self, run_id: str, state: dict[str, NDArray[np.generic]]) -> None:
        run_dir = self.run_dir(run_id)
        arrays: dict[str, Any] = dict(state)
        np.savez(run_dir / "final_state.npz", **arrays)
        metadata = {
            key: {"shape": list(value.shape), "dtype": str(value.dtype)}
            for key, value in state.items()
        }
        self._write_json(run_dir / "final_state.json", metadata)

    def _write_manifest(self, context: RunContext) -> None:
        self._write_json(self.run_dir(context.run_id) / "manifest.json", context.to_manifest())

    def _append_jsonl(self, path: Path, records: list[dict[str, Any]]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True))
                handle.write("\n")

    def _write_json(self, path: Path, value: object) -> None:
        path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
