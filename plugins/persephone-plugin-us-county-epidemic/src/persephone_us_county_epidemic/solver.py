from __future__ import annotations

from typing import Any

import numpy as np
from numpy.random import Generator
from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict

from persephone.solvers.graph import ContactGraph
from persephone_us_county_epidemic.model import sir_step


class USCountySolver(Solver):
    def __init__(self) -> None:
        self.rng = np.random.default_rng(0)
        self.last_events: list[dict[str, Any]] = []
        self._t = 0.0

    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: StateDict, dt: float, bus: Any) -> tuple[StateDict, float]:
        rng = self.rng if isinstance(self.rng, Generator) else np.random.default_rng(0)
        graph = _graph_from_state(state)
        result = sir_step(
            graph,
            state["states"],
            float(state["p_infect"][0]),
            float(state["p_recover"][0]),
            rng,
            t=self._t + dt,
        )
        new_state = {key: value.copy() for key, value in state.items()}
        new_state["states"] = result.states
        new_state["last_new_infections"] = np.array(
            [sum(1 for event in result.events if event["event"] == "infection")],
            dtype=np.int64,
        )
        new_state["last_new_recoveries"] = np.array(
            [sum(1 for event in result.events if event["event"] == "recovery")],
            dtype=np.int64,
        )
        self.last_events = _remap_events(result.events, state["node_geoids"])
        self._t += dt
        if bus is not None:
            bus.write(
                "states",
                new_state["states"],
                solver_id="us_county_epidemic",
                tick=int(self._t),
            )
        return new_state, dt


def _graph_from_state(state: StateDict) -> ContactGraph:
    node_count = int(state["states"].shape[0])
    adjacency: list[list[tuple[int, float]]] = [[] for _ in range(node_count)]
    for source, target, weight in zip(
        state["edge_sources"],
        state["edge_targets"],
        state["edge_weights"],
        strict=True,
    ):
        source_id = int(source)
        target_id = int(target)
        edge_weight = float(weight)
        adjacency[source_id].append((target_id, edge_weight))
        adjacency[target_id].append((source_id, edge_weight))
    return ContactGraph(n_nodes=node_count, adjacency=tuple(tuple(row) for row in adjacency))


def _remap_events(
    events: list[dict[str, Any]],
    node_geoids: np.ndarray[Any, Any],
) -> list[dict[str, Any]]:
    remapped: list[dict[str, Any]] = []
    for event in events:
        payload = dict(event)
        if "entity_id" in payload:
            payload["entity_id"] = _format_geoid(node_geoids[int(payload["entity_id"])])
        if "source_id" in payload:
            payload["source_id"] = _format_geoid(node_geoids[int(payload["source_id"])])
        remapped.append(payload)
    return remapped


def _format_geoid(value: Any) -> str:
    return f"{int(value):05d}"
