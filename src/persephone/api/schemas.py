from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from persephone.config.models import ExperimentConfig
from persephone.frames import FrameListResponse
from persephone.sweeps import ScalarValue, SweepConfig


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str


class RunCreateRequest(BaseModel):
    config: ExperimentConfig
    run_id: str | None = None


class RunSummaryResponse(BaseModel):
    run_id: str
    name: str
    status: Literal["pending", "running", "cancelling", "cancelled", "completed", "failed"]
    started_at: str
    final_time: float
    plugins: list[str]
    config_hash: str
    artifact_path: str | None
    error_message: str | None
    cancel_requested: bool = False


class MetricRecordResponse(BaseModel):
    t: float
    metric: str
    value: float
    run_id: str | None = None
    solver_id: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class EventRecordResponse(BaseModel):
    t: float | None = None
    event: str | None = None
    event_type: str | None = None
    run_id: str | None = None
    solver_id: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class PluginSummaryResponse(BaseModel):
    name: str
    version: str
    paradigm: str
    trust_level: str | None = None

    model_config = {"extra": "allow"}


class ExampleSummaryResponse(BaseModel):
    id: str
    name: str
    description: str


class ExampleConfigResponse(ExampleSummaryResponse):
    config: ExperimentConfig


class SweepCreateRequest(BaseModel):
    name: str
    base_config: ExperimentConfig
    parameter: str
    values: list[ScalarValue]
    sweep_id: str | None = None

    def to_sweep_config(self) -> SweepConfig:
        return SweepConfig(
            sweep_id=self.sweep_id,
            name=self.name,
            base_config=self.base_config,
            parameter=self.parameter,
            values=self.values,
        )


__all__ = [
    "ApiError",
    "EventRecordResponse",
    "ExampleConfigResponse",
    "ExampleSummaryResponse",
    "FrameListResponse",
    "HealthResponse",
    "MetricRecordResponse",
    "PluginSummaryResponse",
    "RunCreateRequest",
    "RunSummaryResponse",
    "SweepCreateRequest",
]
