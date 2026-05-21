from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator


class FrameValidationError(ValueError):
    """Raised when a simulation frame does not match the normalized frame contract."""


class FramePayloadRef(BaseModel):
    uri: str = Field(min_length=1)
    format: Literal["json", "jsonl", "npz", "npy", "zarr", "parquet"]
    byte_offset: int | None = Field(default=None, ge=0)
    byte_length: int | None = Field(default=None, ge=0)


class BaseFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    run_id: str = Field(min_length=1)
    frame_id: str = Field(min_length=1)
    t: float = Field(ge=0)
    tick: int = Field(ge=0)
    solver_id: str = Field(min_length=1)
    source: Literal["live", "replay", "checkpoint", "final_state"] = "live"
    schema_version: int = Field(default=1, ge=1)


class FieldFrame(BaseFrame):
    kind: Literal["field"] = "field"
    field: str = Field(min_length=1)
    shape: tuple[int, int]
    dtype: str = Field(min_length=1)
    bounds: dict[str, float]
    units: str = "unitless"
    visualization: dict[str, Any] = Field(default_factory=dict)
    values: list[float] | None = None
    payload_ref: FramePayloadRef | None = None

    @field_validator("shape")
    @classmethod
    def validate_shape(cls, value: tuple[int, int]) -> tuple[int, int]:
        if value[0] <= 0 or value[1] <= 0:
            raise ValueError("shape dimensions must be positive")
        return value

    @model_validator(mode="after")
    def validate_payload(self) -> FieldFrame:
        if self.values is None and self.payload_ref is None:
            raise ValueError("field frame requires values or payload_ref")
        if self.values is not None and len(self.values) != self.shape[0] * self.shape[1]:
            raise ValueError("values length must match shape")
        return self


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    x: float | None = None
    y: float | None = None
    state: str | None = None


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    weight: float | None = None


class GraphFrame(BaseFrame):
    kind: Literal["graph"] = "graph"
    nodes: list[GraphNode]
    edges: list[GraphEdge] = Field(default_factory=list)
    visualization: dict[str, Any] = Field(default_factory=dict)


SimulationFrame = Annotated[FieldFrame | GraphFrame, Field(discriminator="kind")]
SimulationFrameAdapter: TypeAdapter[SimulationFrame] = TypeAdapter(SimulationFrame)


class FrameIndexEntry(BaseModel):
    frame_id: str = Field(min_length=1)
    kind: Literal["field", "graph"]
    t: float = Field(ge=0)
    tick: int = Field(ge=0)
    solver_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    payload_ref: FramePayloadRef | None = None


class FrameIndex(BaseModel):
    run_id: str = Field(min_length=1)
    frames: list[FrameIndexEntry]


def validate_frame(frame: dict[str, Any]) -> FieldFrame | GraphFrame:
    try:
        validated = SimulationFrameAdapter.validate_python(frame)
        return validated
    except Exception as exc:
        raise FrameValidationError(str(exc)) from exc


__all__ = [
    "BaseFrame",
    "FieldFrame",
    "FrameIndex",
    "FrameIndexEntry",
    "FramePayloadRef",
    "FrameValidationError",
    "GraphEdge",
    "GraphFrame",
    "GraphNode",
    "SimulationFrame",
    "validate_frame",
]
