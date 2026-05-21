from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
from persephone_sdk import __version__ as sdk_version
from persephone_sdk.plugin import PluginManifest

from persephone import __version__ as engine_version
from persephone.config.models import ExperimentConfig

RunStatus = str


@dataclass
class RunContext:
    run_id: str
    status: RunStatus
    config_snapshot: dict[str, object]
    config_hash: str
    engine_version: str
    sdk_version: str
    plugin_versions: dict[str, str]
    seed: int
    seed_plan: dict[str, int]
    started_at: str
    t_current: float = 0.0
    error_message: str | None = None
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    platform: str = field(default_factory=platform.platform)
    dependency_lock_hash: str | None = None
    runtime_backend: str = "python"
    runtime_version: str = engine_version
    frame_artifacts_path: str = "frames/index.json"

    @classmethod
    def create(
        cls,
        config: ExperimentConfig,
        plugin_manifests: dict[str, PluginManifest],
        run_id: str | None = None,
    ) -> RunContext:
        config_snapshot = config.model_dump(mode="json")
        seed_plan = create_seed_plan(config)
        plugin_versions = {
            plugin_name: plugin_manifests[plugin_name].version
            for plugin_name in sorted(plugin_manifests)
        }

        return cls(
            run_id=run_id or str(uuid4()),
            status="pending",
            config_snapshot=config_snapshot,
            config_hash=hash_json(config_snapshot),
            engine_version=engine_version,
            sdk_version=sdk_version,
            plugin_versions=plugin_versions,
            seed=config.seed,
            seed_plan=seed_plan,
            started_at=datetime.now(tz=UTC).isoformat(),
            dependency_lock_hash=hash_file(Path("uv.lock")),
        )

    def to_manifest(self) -> dict[str, object]:
        return asdict(self)

    def mark_status(
        self, status: RunStatus, t_current: float | None = None, error_message: str | None = None
    ) -> None:
        self.status = status
        if t_current is not None:
            self.t_current = t_current
        self.error_message = error_message


def create_seed_plan(config: ExperimentConfig) -> dict[str, int]:
    seed_sequence = np.random.SeedSequence(config.seed)
    children = seed_sequence.spawn(len(config.solvers))
    seed_plan: dict[str, int] = {}

    for index, (solver, child) in enumerate(zip(config.solvers, children, strict=True)):
        key = f"{solver.plugin}#{index}"
        seed_plan[key] = int(child.generate_state(1, dtype=np.uint32)[0])

    return seed_plan


def hash_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hash_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()
