from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class RecordValidationError(ValueError):
    """Raised when persisted simulation records do not match core schemas."""


class CoreRecord(BaseModel):
    model_config = ConfigDict(extra="allow")


class MetricRecord(CoreRecord):
    run_id: str = Field(min_length=1)
    solver_id: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: float
    t: float
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("tags must be a mapping")
        return {str(key): str(item) for key, item in value.items()}

    @classmethod
    def validate_many(cls, records: list[dict[str, Any]]) -> list[MetricRecord]:
        try:
            return [cls.model_validate(record) for record in records]
        except ValidationError as exc:
            raise RecordValidationError(str(exc)) from exc


class EventRecord(CoreRecord):
    run_id: str = Field(min_length=1)
    solver_id: str = Field(min_length=1)
    event: str = Field(min_length=1)
    t: float
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("tags must be a mapping")
        return {str(key): str(item) for key, item in value.items()}

    @classmethod
    def validate_many(cls, records: list[dict[str, Any]]) -> list[EventRecord]:
        try:
            return [cls.model_validate(record) for record in records]
        except ValidationError as exc:
            raise RecordValidationError(str(exc)) from exc


class SchedulerTelemetry(BaseModel):
    tick: int = Field(ge=0)
    logical_time: float = Field(ge=0)
    wall_time_ms: float = Field(ge=0)
    sync_interval_used: float = Field(gt=0)
    solver_step_times: dict[str, float] = Field(default_factory=dict)
    cfl_constrained: bool = False
    coupling_conflicts: dict[str, int] = Field(default_factory=dict)
    coupling_rules: dict[str, str] = Field(default_factory=dict)
    bus_channel_sizes: dict[str, int] = Field(default_factory=dict)

    def to_metric_records(self, run_id: str) -> list[dict[str, Any]]:
        tags = {
            "tick": str(self.tick),
            "sync_interval_used": f"{self.sync_interval_used:g}",
            "cfl_constrained": str(self.cfl_constrained).lower(),
        }
        records = [
            {
                "run_id": run_id,
                "solver_id": "scheduler",
                "metric": "scheduler.wall_time_ms",
                "value": self.wall_time_ms,
                "t": self.logical_time,
                "tags": tags,
            },
            {
                "run_id": run_id,
                "solver_id": "scheduler",
                "metric": "scheduler.sync_interval_used",
                "value": self.sync_interval_used,
                "t": self.logical_time,
                "tags": tags,
            },
        ]
        for solver_id, elapsed_ms in sorted(self.solver_step_times.items()):
            records.append(
                {
                    "run_id": run_id,
                    "solver_id": "scheduler",
                    "metric": "scheduler.solver_step_time_ms",
                    "value": elapsed_ms,
                    "t": self.logical_time,
                    "tags": {**tags, "solver_id": solver_id},
                }
            )
        return records


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    run_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    config_snapshot: dict[str, Any]
    config_hash: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    sdk_version: str = Field(min_length=1)
    plugin_versions: dict[str, str]
    seed: int
    seed_plan: dict[str, int]
    started_at: str
    t_current: float = 0.0
    error_message: str | None = None


StateValueKind = Literal["ndarray", "sparse", "masked"]
