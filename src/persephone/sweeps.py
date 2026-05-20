from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from persephone.config.models import ExperimentConfig
from persephone.core.engine import PersephoneEngine

ScalarValue = bool | int | float | str
_PATH_TOKEN_RE = re.compile(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\[(?P<index>\d+)])?")


class SweepConfig(BaseModel):
    name: str = Field(min_length=1)
    base_config: ExperimentConfig
    parameter: str = Field(min_length=1)
    values: list[ScalarValue] = Field(min_length=1)
    sweep_id: str | None = None

    @model_validator(mode="after")
    def set_sweep_id(self) -> SweepConfig:
        if self.sweep_id is None:
            self.sweep_id = f"sweep-{uuid4().hex[:12]}"
        return self


class SweepChildRun(BaseModel):
    run_id: str
    value: ScalarValue
    status: str
    artifact_path: str


class SweepManifest(BaseModel):
    sweep_id: str
    name: str
    parameter: str
    values: list[ScalarValue]
    created_at: str
    child_runs: list[SweepChildRun]


@dataclass(frozen=True)
class GeneratedSweepRun:
    run_id: str
    value: ScalarValue
    config: ExperimentConfig


def generate_sweep_configs(sweep: SweepConfig) -> list[GeneratedSweepRun]:
    sweep_id = _require_sweep_id(sweep)
    generated: list[GeneratedSweepRun] = []
    for index, value in enumerate(sweep.values, start=1):
        raw_config = sweep.base_config.model_dump(mode="json")
        set_dotted_path(raw_config, sweep.parameter, value)
        generated.append(
            GeneratedSweepRun(
                run_id=f"{sweep_id}-{index:03d}",
                value=value,
                config=ExperimentConfig.model_validate(raw_config),
            )
        )
    return generated


def execute_sweep(
    sweep: SweepConfig,
    artifact_root: str | Path = "runs",
    engine_factory: Callable[[Path], PersephoneEngine] | None = None,
) -> SweepManifest:
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    child_runs: list[SweepChildRun] = []
    make_engine = engine_factory or (
        lambda artifact_path: PersephoneEngine(artifact_root=artifact_path)
    )

    for child in generate_sweep_configs(sweep):
        result = make_engine(root).run(child.config, run_id=child.run_id)
        _link_child_manifest(
            result.artifact_path / "manifest.json",
            sweep_id=_require_sweep_id(sweep),
            parameter=sweep.parameter,
            value=child.value,
        )
        child_runs.append(
            SweepChildRun(
                run_id=result.run_id,
                value=child.value,
                status=result.status,
                artifact_path=str(result.artifact_path),
            )
        )

    manifest = SweepManifest(
        sweep_id=_require_sweep_id(sweep),
        name=sweep.name,
        parameter=sweep.parameter,
        values=sweep.values,
        created_at=datetime.now(tz=UTC).isoformat(),
        child_runs=child_runs,
    )
    sweep_dir = root / manifest.sweep_id
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def set_dotted_path(target: dict[str, Any], path: str, value: ScalarValue) -> None:
    current: Any = target
    tokens = _parse_dotted_path(path)
    for name, index in tokens[:-1]:
        current = _descend(current, name, index)

    final_name, final_index = tokens[-1]
    if not isinstance(current, dict) or final_name not in current:
        raise ValueError(f"Sweep parameter path does not exist: {path}")
    if final_index is None:
        current[final_name] = value
        return
    sequence = current[final_name]
    if not isinstance(sequence, list) or final_index >= len(sequence):
        raise ValueError(f"Sweep parameter path does not exist: {path}")
    sequence[final_index] = value


def _descend(current: Any, name: str, index: int | None) -> Any:
    if not isinstance(current, dict) or name not in current:
        raise ValueError(f"Sweep parameter path does not exist at '{name}'")
    next_value = current[name]
    if index is None:
        return next_value
    if not isinstance(next_value, list) or index >= len(next_value):
        raise ValueError(f"Sweep parameter index does not exist: {name}[{index}]")
    return next_value[index]


def _parse_dotted_path(path: str) -> list[tuple[str, int | None]]:
    tokens: list[tuple[str, int | None]] = []
    for raw_token in path.split("."):
        match = _PATH_TOKEN_RE.fullmatch(raw_token)
        if match is None:
            raise ValueError(f"Invalid sweep parameter path token: {raw_token}")
        index = match.group("index")
        tokens.append((match.group("name"), int(index) if index is not None else None))
    if not tokens:
        raise ValueError("Sweep parameter path cannot be empty")
    return tokens


def _link_child_manifest(
    manifest_path: Path,
    *,
    sweep_id: str,
    parameter: str,
    value: ScalarValue,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sweep_id"] = sweep_id
    manifest["sweep_parameter"] = parameter
    manifest["sweep_value"] = value
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _require_sweep_id(sweep: SweepConfig) -> str:
    if sweep.sweep_id is None:
        raise ValueError("Sweep id was not initialized")
    return sweep.sweep_id
