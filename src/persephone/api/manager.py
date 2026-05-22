from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from persephone.config.models import ExperimentConfig
from persephone.core.engine import PersephoneEngine, RunResult
from persephone.core.explanations import ExplanationPacket, validate_explanation_packet
from persephone.core.run import RunContext
from persephone.frames import get_frame, list_frames
from persephone.storage.catalog import RunCatalog, RunNotFoundError, RunSummary

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
FRAME_STREAM_BUFFER_LIMIT = 512
SSE_STREAM_BUFFER_LIMIT = 2_048


@dataclass
class ManagedRun:
    run_id: str
    status: str = "pending"
    artifact_path: Path | None = None
    final_time: float = 0.0
    error_message: str | None = None
    plugins: list[str] = field(default_factory=list)
    config_hash: str = ""
    metric_events: list[dict[str, Any]] = field(default_factory=list)
    data_events: list[dict[str, Any]] = field(default_factory=list)
    frame_events: list[tuple[int, dict[str, Any]]] = field(default_factory=list)
    frame_sequence: int = 0
    stream_events: list[tuple[int, str, dict[str, Any]]] = field(default_factory=list)
    event_sequence: int = 0
    result: RunResult | None = None
    cancel_requested: bool = False


class RunManager:
    def __init__(self, artifact_root: str | Path = "runs") -> None:
        self.artifact_root = Path(artifact_root)
        self._runs: dict[str, ManagedRun] = {}
        self._lock = threading.Lock()

    def start(self, config: ExperimentConfig, run_id: str | None = None) -> ManagedRun:
        requested_id = run_id or str(uuid4())
        managed = ManagedRun(
            run_id=requested_id,
            artifact_path=self.artifact_root / requested_id,
            plugins=[solver.plugin for solver in config.solvers],
            config_hash=RunContext.create(config, {}, run_id=requested_id).config_hash,
        )
        with self._lock:
            self._runs[requested_id] = managed

        thread = threading.Thread(
            target=self._run_in_background,
            args=(config, requested_id, managed),
            daemon=True,
        )
        thread.start()
        return managed

    def get(self, run_id: str) -> RunSummary | ManagedRun:
        with self._lock:
            managed = self._runs.get(run_id)
            if managed is not None:
                if managed.status in TERMINAL_STATUSES and managed.artifact_path is not None:
                    break_catalog = True
                else:
                    break_catalog = False
            else:
                break_catalog = True
            if managed is not None and not break_catalog:
                return managed
        return RunCatalog.scan(self.artifact_root).get(run_id)

    def list_runs(self, status: str | None = None) -> list[RunSummary | ManagedRun]:
        catalog_runs = RunCatalog.scan(self.artifact_root).list_runs(status=status)
        with self._lock:
            active_runs = list(self._runs.values())
        active_runs = [
            run
            for run in active_runs
            if not (run.status in TERMINAL_STATUSES and run.artifact_path is not None)
        ]
        if status is not None:
            active_runs = [run for run in active_runs if run.status == status]
        active_ids = {run.run_id for run in active_runs}
        return [*active_runs, *[run for run in catalog_runs if run.run_id not in active_ids]]

    def metric_records(self, run_id: str, metric: str | None = None) -> list[dict[str, Any]]:
        records = _read_jsonl(_run_path(self.get(run_id)) / "metrics.jsonl")
        if metric is not None:
            records = [record for record in records if record.get("metric") == metric]
        return records

    def event_records(self, run_id: str) -> list[dict[str, Any]]:
        return _read_jsonl(_run_path(self.get(run_id)) / "events.jsonl")

    def explanation_packets(self, run_id: str) -> list[ExplanationPacket]:
        records = _read_jsonl(_run_path(self.get(run_id)) / "explanations" / "facts.jsonl")
        return [validate_explanation_packet(record) for record in records]

    def run_context(self, run_id: str) -> RunContext:
        manifest = _read_json(_run_path(self.get(run_id)) / "manifest.json")
        return RunContext(**manifest)

    def request_cancel(self, run_id: str) -> ManagedRun:
        with self._lock:
            managed = self._runs.get(run_id)
            if managed is None:
                raise RunNotFoundError(f"Active run not found: {run_id}")
            managed.cancel_requested = True
            if managed.status in {"pending", "running"}:
                managed.status = "cancelling"
            return managed

    def sse_metric_events(self, run_id: str) -> Iterator[str]:
        yielded = 0
        while True:
            with self._lock:
                managed = self._runs.get(run_id)
                in_memory = list(managed.metric_events) if managed else []
                status = managed.status if managed else None

            for event in in_memory[yielded:]:
                yielded += 1
                yield _to_sse("metric", event)

            if status in {None, *TERMINAL_STATUSES}:
                break

        if yielded == 0:
            for record in self.metric_records(run_id):
                yield _to_sse("metric", record)

    def sse_frame_events(self, run_id: str, last_event_id: str | None = None) -> Iterator[str]:
        last_seen = _parse_last_event_id(last_event_id)
        yielded = 0
        while True:
            with self._lock:
                managed = self._runs.get(run_id)
                in_memory = list(managed.stream_events) if managed else []
                status = managed.status if managed else None
                error_message = managed.error_message if managed else None

            for sequence_id, event_name, event in in_memory:
                if sequence_id <= last_seen:
                    continue
                yielded += 1
                last_seen = sequence_id
                yield _to_sse(event_name, event, event_id=sequence_id)

            if status in {None, *TERMINAL_STATUSES}:
                if status == "failed":
                    yield _to_sse(
                        "error",
                        {"run_id": run_id, "message": error_message or "Run failed"},
                    )
                yield _to_sse("status", {"run_id": run_id, "status": status or "completed"})
                break

            if yielded == 0:
                yield _to_sse("heartbeat", {"run_id": run_id, "status": status})
            time.sleep(0.05)

        if yielded == 0:
            for sequence_id, entry in enumerate(list_frames(self.artifact_root, run_id).frames, 1):
                if sequence_id <= last_seen:
                    continue
                yield _to_sse(
                    "frame",
                    get_frame(self.artifact_root, run_id, entry.frame_id),
                    event_id=sequence_id,
                )

    def _run_in_background(
        self,
        config: ExperimentConfig,
        requested_run_id: str | None,
        managed: ManagedRun,
    ) -> None:
        def on_record(kind: str, record: dict[str, Any]) -> None:
            with self._lock:
                if kind == "metric":
                    managed.metric_events.append(record)
                elif kind == "event":
                    managed.data_events.append(record)
                elif kind == "frame":
                    managed.frame_sequence += 1
                    managed.frame_events.append((managed.frame_sequence, record))
                    if len(managed.frame_events) > FRAME_STREAM_BUFFER_LIMIT:
                        managed.frame_events = managed.frame_events[-FRAME_STREAM_BUFFER_LIMIT:]
                if kind in {"metric", "event", "frame"}:
                    managed.event_sequence += 1
                    managed.stream_events.append((managed.event_sequence, kind, record))
                    if len(managed.stream_events) > SSE_STREAM_BUFFER_LIMIT:
                        managed.stream_events = managed.stream_events[-SSE_STREAM_BUFFER_LIMIT:]

        try:
            with self._lock:
                managed.status = "running"

            result = PersephoneEngine(artifact_root=self.artifact_root).run(
                config,
                run_id=requested_run_id,
                record_callback=on_record,
                should_cancel=lambda: managed.cancel_requested,
            )
            with self._lock:
                managed.run_id = result.run_id
                managed.status = result.status
                managed.artifact_path = result.artifact_path
                managed.final_time = result.final_time
                managed.error_message = result.error_message
                managed.result = result
                self._runs[result.run_id] = managed
        except Exception as exc:  # noqa: BLE001 - manager keeps API boundary alive.
            with self._lock:
                managed.status = "failed"
                managed.error_message = str(exc)


def serialize_run(run: RunSummary | ManagedRun) -> dict[str, Any]:
    if isinstance(run, RunSummary):
        return {
            "run_id": run.run_id,
            "name": run.name,
            "status": run.status,
            "started_at": run.started_at,
            "final_time": run.final_time,
            "plugins": run.plugins,
            "config_hash": run.config_hash,
            "artifact_path": str(run.path),
            "error_message": run.error_message,
            "cancel_requested": False,
        }

    return {
        "run_id": run.run_id,
        "name": "",
        "status": run.status,
        "started_at": "",
        "final_time": run.final_time,
        "plugins": [],
        "plugins": run.plugins,
        "config_hash": run.config_hash,
        "artifact_path": str(run.artifact_path) if run.artifact_path else None,
        "error_message": run.error_message,
        "cancel_requested": run.cancel_requested,
    }


def _run_path(run: RunSummary | ManagedRun) -> Path:
    if isinstance(run, RunSummary):
        return run.path
    if run.artifact_path is None:
        raise RunNotFoundError(f"Run artifacts are not ready yet: {run.run_id}")
    return run.artifact_path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RunNotFoundError(f"Run metadata is not ready yet: {path}")
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _to_sse(event: str, data: dict[str, Any], event_id: int | None = None) -> str:
    prefix = f"id: {event_id}\n" if event_id is not None else ""
    return f"{prefix}event: {event}\ndata: {json.dumps(data, sort_keys=True)}\n\n"


def _parse_last_event_id(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        return 0
