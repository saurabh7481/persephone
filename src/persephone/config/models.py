from __future__ import annotations

from typing import Any, Literal

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import BaseModel, ConfigDict, Field, field_validator

from persephone.core.coupling import coupling_registry

Paradigm = Literal["ode", "pde", "abm", "graph", "sde", "hybrid"]
SyncInterval = float | Literal["auto"]
SplittingOrder = Literal["first_order", "strang"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SchedulerConfig(StrictModel):
    t_end: float = Field(gt=0)
    sync_interval: SyncInterval = "auto"
    dt: float | None = Field(default=None, gt=0)
    ensemble_size: int | None = Field(default=None, gt=0)
    checkpoint_every: int | None = Field(default=None, gt=0)
    demo_delay_ms_per_tick: int = Field(default=0, ge=0)
    splitting_order: SplittingOrder = "first_order"

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
    rules: dict[str, str] = Field(default_factory=dict)

    @field_validator("rules")
    @classmethod
    def validate_registered_rules(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = sorted({rule for rule in value.values() if not coupling_registry.has(rule)})
        if unknown:
            allowed = ", ".join(coupling_registry.names())
            raise ValueError(
                f"Unknown coupling rule(s): {', '.join(unknown)}. Registered rules: {allowed}"
            )
        return value


class VisualizationConfig(StrictModel):
    emit_every: float = Field(default=1.0, gt=0)
    inline_frame_max_values: int = Field(default=4096, gt=0)


class ExperimentConfig(StrictModel):
    name: str = Field(min_length=1)
    seed: int
    scheduler: SchedulerConfig
    solvers: list[SolverConfig] = Field(min_length=1)
    observer: ObserverConfig = Field(default_factory=ObserverConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    coupling: CouplingConfig = Field(default_factory=CouplingConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    description: str | None = None
