from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class RunCatalogError(RuntimeError):
    """Base error for run catalog failures."""


class DuplicateRunIdError(RunCatalogError):
    """Raised when two scanned roots contain the same run id."""


class RunNotFoundError(RunCatalogError):
    """Raised when a run id or path cannot be resolved."""


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    name: str
    status: str
    started_at: str
    final_time: float
    plugins: list[str]
    config_hash: str
    path: Path
    error_message: str | None = None


class RunCatalog:
    def __init__(self, roots: list[Path], runs: dict[str, RunSummary]) -> None:
        self.roots = roots
        self._runs = runs

    @classmethod
    def scan(cls, roots: str | Path | list[str | Path] | tuple[str | Path, ...]) -> RunCatalog:
        root_paths = (
            [Path(root) for root in roots] if isinstance(roots, list | tuple) else [Path(roots)]
        )
        runs: dict[str, RunSummary] = {}

        for root in root_paths:
            if not root.exists():
                continue
            for manifest_path in sorted(root.glob("*/manifest.json")):
                summary = read_run_summary(manifest_path.parent)
                if summary.run_id in runs:
                    raise DuplicateRunIdError(
                        f"Duplicate run id '{summary.run_id}' in "
                        f"{runs[summary.run_id].path} and {summary.path}"
                    )
                runs[summary.run_id] = summary

        return cls(root_paths, runs)

    def list_runs(self, status: str | None = None) -> list[RunSummary]:
        runs = list(self._runs.values())
        if status is not None:
            runs = [run for run in runs if run.status == status]
        return sorted(runs, key=lambda run: (run.started_at, run.run_id), reverse=True)

    def get(self, run_id_or_path: str | Path) -> RunSummary:
        candidate = Path(run_id_or_path)
        if candidate.exists():
            return read_run_summary(candidate)

        run_id = str(run_id_or_path)
        if run_id in self._runs:
            return self._runs[run_id]

        raise RunNotFoundError(f"Run not found: {run_id_or_path}")


def read_run_summary(run_dir: str | Path) -> RunSummary:
    path = Path(run_dir)
    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        raise RunNotFoundError(f"Run manifest does not exist: {manifest_path}")

    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    config = cast(dict[str, Any], manifest.get("config_snapshot", {}))
    solvers = cast(list[dict[str, Any]], config.get("solvers", []))
    plugin_versions = cast(dict[str, str], manifest.get("plugin_versions", {}))
    plugins = sorted(plugin_versions) or sorted(
        str(solver.get("plugin")) for solver in solvers if solver.get("plugin")
    )

    return RunSummary(
        run_id=str(manifest["run_id"]),
        name=str(config.get("name", manifest["run_id"])),
        status=str(manifest.get("status", "unknown")),
        started_at=str(manifest.get("started_at", "")),
        final_time=float(cast(float | int, manifest.get("t_current", 0.0))),
        plugins=plugins,
        config_hash=str(manifest.get("config_hash", "")),
        path=path,
        error_message=(
            str(manifest["error_message"]) if manifest.get("error_message") is not None else None
        ),
    )
