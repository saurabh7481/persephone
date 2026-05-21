from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from persephone.config.models import ExperimentConfig
from persephone.core.engine import PersephoneEngine, RunResult
from persephone.storage.catalog import RunCatalog


@dataclass(frozen=True)
class RuntimeCapability:
    backend: str
    version: str
    supports_live_frames: bool
    supports_replay: bool
    supports_pause_resume: bool
    max_recommended_frame_rate: float


class SimulationRuntime(Protocol):
    def validate(self, config: ExperimentConfig) -> dict[str, object]: ...

    def start_run(
        self,
        config: ExperimentConfig,
        run_id: str | None = None,
        record_callback: Callable[[str, dict[str, Any]], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> RunResult: ...

    def cancel_run(self, run_id: str) -> None: ...

    def stream_records(self, run_id: str) -> Iterator[tuple[str, dict[str, Any]]]: ...

    def list_artifacts(self, run_id: str) -> list[Path]: ...

    def runtime_capabilities(self) -> RuntimeCapability: ...


class PythonSimulationRuntime:
    def __init__(self, artifact_root: str | Path = "runs") -> None:
        self.artifact_root = Path(artifact_root)
        self.engine = PersephoneEngine(artifact_root=self.artifact_root)

    def validate(self, config: ExperimentConfig) -> dict[str, object]:
        manifests = self.engine.validate(config)
        return {
            name: {
                "name": manifest.name,
                "version": manifest.version,
                "paradigm": manifest.paradigm,
            }
            for name, manifest in manifests.items()
        }

    def start_run(
        self,
        config: ExperimentConfig,
        run_id: str | None = None,
        record_callback: Callable[[str, dict[str, Any]], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> RunResult:
        return self.engine.run(
            config,
            run_id=run_id,
            record_callback=record_callback,
            should_cancel=should_cancel,
        )

    def cancel_run(self, run_id: str) -> None:
        raise NotImplementedError("PythonSimulationRuntime cancellation is managed by RunManager")

    def stream_records(self, run_id: str) -> Iterator[tuple[str, dict[str, Any]]]:
        run_dir = RunCatalog.scan(self.artifact_root).get(run_id).path
        for kind, path in (
            ("metric", run_dir / "metrics.jsonl"),
            ("event", run_dir / "events.jsonl"),
        ):
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield kind, json.loads(line)

    def list_artifacts(self, run_id: str) -> list[Path]:
        run_dir = RunCatalog.scan(self.artifact_root).get(run_id).path
        return sorted(path for path in run_dir.rglob("*") if path.is_file())

    def runtime_capabilities(self) -> RuntimeCapability:
        from persephone import __version__

        return RuntimeCapability(
            backend="python",
            version=__version__,
            supports_live_frames=True,
            supports_replay=True,
            supports_pause_resume=False,
            max_recommended_frame_rate=30.0,
        )
