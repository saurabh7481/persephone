from __future__ import annotations

from typing import Any, TypeAlias, TypedDict

import numpy as np

StateValue: TypeAlias = np.ndarray | np.ma.MaskedArray
WorldState: TypeAlias = dict[str, StateValue]
StateDict: TypeAlias = WorldState


class MetricRecord(TypedDict, total=False):
    run_id: str
    solver_id: str
    metric: str
    value: float
    t: float
    tags: dict[str, str]


class EventRecord(TypedDict, total=False):
    run_id: str
    solver_id: str
    event: str
    t: float
    tags: dict[str, str]


class BusRecord(TypedDict, total=False):
    run_id: str
    tick: int
    solver_id: str
    schema_id: str
    logical_time: float
    value: Any
    units: str | None


class FramePayloadRef(TypedDict, total=False):
    uri: str
    format: str
    byte_offset: int | None
    byte_length: int | None


class FieldFrame(TypedDict, total=False):
    kind: str
    run_id: str
    frame_id: str
    t: float
    tick: int
    solver_id: str
    source: str
    schema_version: int
    field: str
    shape: tuple[int, int]
    dtype: str
    bounds: dict[str, float]
    units: str
    visualization: dict[str, Any]
    values: list[float]
    payload_ref: FramePayloadRef


class GraphNode(TypedDict, total=False):
    id: str
    x: float | None
    y: float | None
    state: str | None
    label: str | None
    group: str | None
    lat: float | None
    lon: float | None
    metrics: dict[str, float]
    attrs: dict[str, Any]


class GraphEdge(TypedDict, total=False):
    source: str
    target: str
    weight: float | None
    kind: str | None
    directed: bool | None
    attrs: dict[str, Any]


class GraphVisualization(TypedDict, total=False):
    layout_hint: str | None
    coordinate_system: str | None
    preferred_view: str | None
    legend: dict[str, Any]
    selection_schema: dict[str, Any]
    density_hint: str | None


class GraphFrame(TypedDict, total=False):
    kind: str
    run_id: str
    frame_id: str
    t: float
    tick: int
    solver_id: str
    source: str
    schema_version: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    visualization: GraphVisualization


SimulationFrame: TypeAlias = FieldFrame | GraphFrame
