from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, cast

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict

from persephone.solvers.graph import INFECTED, SUSCEPTIBLE, ContactGraph


class SIRWorld(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        if self._initial is None:
            return {"states": (0,)}
        return {key: value.shape for key, value in self._initial.items()}

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        graph_path = Path(str(params["contact_graph"]))
        n_nodes = int(params["n_nodes"])
        graph = ContactGraph.from_csv(graph_path, n_nodes=n_nodes)
        sources, targets, weights = _read_edges(graph_path)
        states = np.full(graph.n_nodes, SUSCEPTIBLE, dtype=np.int8)
        initially_infected = _initial_infections(params["initially_infected"], graph.n_nodes, seed)
        states[initially_infected] = INFECTED

        self._initial = {
            "states": states,
            "edge_sources": sources,
            "edge_targets": targets,
            "edge_weights": weights,
            "p_infect": np.array([float(params["p_infect"])], dtype=np.float64),
            "p_recover": np.array([float(params["p_recover"])], dtype=np.float64),
            "last_new_infections": np.array([0], dtype=np.int64),
            "last_new_recoveries": np.array([0], dtype=np.int64),
        }
        return {key: value.copy() for key, value in self._initial.items()}

    def reset(self) -> StateDict:
        if self._initial is None:
            raise RuntimeError("World has not been initialized")
        return {key: value.copy() for key, value in self._initial.items()}


def _read_edges(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sources: list[int] = []
    targets: list[int] = []
    weights: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sources.append(int(row["source"]))
            targets.append(int(row["target"]))
            weights.append(float(row["weight"]))
    return (
        np.asarray(sources, dtype=np.int64),
        np.asarray(targets, dtype=np.int64),
        np.asarray(weights, dtype=np.float64),
    )


def _initial_infections(value: object, n_nodes: int, seed: int) -> np.ndarray:
    if isinstance(value, list):
        infections = np.asarray(value, dtype=np.int64)
    else:
        count = int(cast(str | int | float, value))
        if count < 1:
            raise ValueError("initially_infected must be at least 1")
        rng = np.random.default_rng(seed)
        infections = np.asarray(rng.choice(n_nodes, size=min(count, n_nodes), replace=False))

    if np.any(infections < 0) or np.any(infections >= n_nodes):
        raise ValueError("initially_infected contains node ids outside n_nodes")
    return infections
