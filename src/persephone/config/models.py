from __future__ import annotations

from typing import Any, Literal

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import BaseModel, ConfigDict, Field, field_validator

Paradigm = Literal["ode", "pde", "abm", "graph", "sde", "hybrid"]
SyncInterval = float | Literal["auto"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SchedulerConfig(StrictModel):
    t_end: float = Field(gt=0)
    sync_interval: SyncInterval = "auto"
    dt: float | None = Field(default=None, gt=0)
    ensemble_size: int | None = Field(default=None, gt=0)

    @field_validator("sync_interval")
    @classmethod
    def validate_sync_interval(cls, value: SyncInterval) -> SyncInterval:
        if value == "auto":
            return value
        if value <= 0:
            raise ValueError("sync_interval must be positive or 'auto'")
        return value


class SolverConfig(StrictModel):
    type: Paradigm
    plugin: str = Field(min_length=1)
    version: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("version")
    @classmethod
    def validate_version_specifier(cls, value: str) -> str:
        try:
            SpecifierSet(value)
        except InvalidSpecifier as exc:
            raise ValueError(f"Invalid plugin version constraint: {value}") from exc
        return value


class ObserverConfig(StrictModel):
    metrics: list[str] = Field(default_factory=list)
    emit_every: float = Field(default=1.0, gt=0)


class StorageConfig(StrictModel):
    artifacts_dir: str = "runs"
    metrics: bool = True
    events: bool = True


class CouplingConfig(StrictModel):
    rules: dict[str, Literal["sum", "mean", "max", "min", "last"]] = Field(default_factory=dict)


class ExperimentConfig(StrictModel):
    name: str = Field(min_length=1)
    seed: int
    scheduler: SchedulerConfig
    solvers: list[SolverConfig] = Field(min_length=1)
    observer: ObserverConfig = Field(default_factory=ObserverConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    coupling: CouplingConfig = Field(default_factory=CouplingConfig)
    description: str | None = None
