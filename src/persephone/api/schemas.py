from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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


class EntityField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    type: Literal["string", "integer", "number", "boolean", "categorical", "enum", "json"]
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    required: bool = False


class StateDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    kind: Literal["categorical", "continuous", "ordinal", "boolean"]
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    values: list[str] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    label: str | None = None
    kind: Literal["scalar", "ratio", "delta", "index"] = "scalar"
    description: str | None = None
    unit: str | None = None
    headline: bool = False


class EventDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    label: str | None = None
    description: str | None = None
    related_entity: str | None = None


class ViewCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "network",
        "positioned_graph",
        "map_network",
        "matrix",
        "table",
        "timeline",
        "heatmap",
        "hierarchy",
    ]
    label: str | None = None
    description: str | None = None
    default: bool = False
    requires_coordinates: bool = False


class ExplanationCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["run", "frame", "selection"]
    label: str | None = None
    description: str | None = None
    fact_kinds: list[str] = Field(default_factory=list)


class SemanticManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_schemas: dict[str, list[EntityField]] = Field(default_factory=dict)
    state_schema: dict[str, StateDefinition] = Field(default_factory=dict)
    metric_schema: dict[str, MetricDefinition] = Field(default_factory=dict)
    event_schema: dict[str, EventDefinition] = Field(default_factory=dict)
    view_capabilities: list[ViewCapability] = Field(default_factory=list)
    explanation_capabilities: list[ExplanationCapability] = Field(default_factory=list)
    default_entity_type: str | None = None
    preferred_view: str | None = None


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
    "EntityField",
    "EventRecordResponse",
    "EventDefinition",
    "ExampleConfigResponse",
    "ExampleSummaryResponse",
    "ExplanationCapability",
    "FrameListResponse",
    "HealthResponse",
    "MetricDefinition",
    "MetricRecordResponse",
    "PluginSummaryResponse",
    "RunCreateRequest",
    "RunSummaryResponse",
    "SemanticManifest",
    "StateDefinition",
    "SweepCreateRequest",
    "ViewCapability",
]
