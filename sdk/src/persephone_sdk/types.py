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
