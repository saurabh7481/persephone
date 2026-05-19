from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray

SUSCEPTIBLE = 0
INFECTED = 1
RECOVERED = 2


@dataclass(frozen=True)
class ContactGraph:
    n_nodes: int
    adjacency: tuple[tuple[tuple[int, float], ...], ...]

    @classmethod
    def from_csv(cls, path: str | Path, n_nodes: int | None = None) -> ContactGraph:
        edge_rows: list[tuple[int, int, float]] = []
        max_node = -1
        with Path(path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"source", "target", "weight"}
            if set(reader.fieldnames or []) < required:
                raise ValueError("Contact graph CSV must include source,target,weight columns")
            for row in reader:
                source = int(row["source"])
                target = int(row["target"])
                weight = float(row["weight"])
                if source < 0 or target < 0:
                    raise ValueError("Node ids must be non-negative")
                if weight < 0:
                    raise ValueError("Edge weights must be non-negative")
                edge_rows.append((source, target, weight))
                max_node = max(max_node, source, target)

        inferred_nodes = max_node + 1
        node_count = inferred_nodes if n_nodes is None else n_nodes
        if node_count < inferred_nodes:
            raise ValueError(f"n_nodes={node_count} cannot contain node id {max_node}")

        adjacency: list[list[tuple[int, float]]] = [[] for _ in range(node_count)]
        for source, target, weight in edge_rows:
            adjacency[source].append((target, weight))
            adjacency[target].append((source, weight))

        return cls(
            n_nodes=node_count,
            adjacency=tuple(tuple(neighbors) for neighbors in adjacency),
        )

    def neighbors(self, node_id: int) -> list[tuple[int, float]]:
        return list(self.adjacency[node_id])


@dataclass(frozen=True)
class SIRStepResult:
    states: NDArray[np.int8]
    events: list[dict[str, Any]]


def sir_step(
    graph: ContactGraph,
    states: NDArray[np.int8],
    p_infect: float,
    p_recover: float,
    rng: Generator,
    t: float,
) -> SIRStepResult:
    if states.shape != (graph.n_nodes,):
        raise ValueError(f"states must have shape ({graph.n_nodes},)")
    if not 0 <= p_infect <= 1:
        raise ValueError("p_infect must be between 0 and 1")
    if not 0 <= p_recover <= 1:
        raise ValueError("p_recover must be between 0 and 1")

    previous = states.copy()
    next_states = previous.copy()
    events: list[dict[str, Any]] = []
    newly_infected: set[int] = set()

    infected_nodes = np.flatnonzero(previous == INFECTED)
    for source in infected_nodes:
        for target, weight in graph.neighbors(int(source)):
            if previous[target] != SUSCEPTIBLE or target in newly_infected:
                continue
            probability = min(1.0, p_infect * weight)
            if rng.random() <= probability:
                newly_infected.add(target)
                next_states[target] = INFECTED
                events.append(
                    {
                        "event": "infection",
                        "entity_id": int(target),
                        "source_id": int(source),
                        "old_state": "susceptible",
                        "new_state": "infected",
                        "t": t,
                    }
                )

    for node_id in infected_nodes:
        if rng.random() <= p_recover:
            next_states[node_id] = RECOVERED
            events.append(
                {
                    "event": "recovery",
                    "entity_id": int(node_id),
                    "old_state": "infected",
                    "new_state": "recovered",
                    "t": t,
                }
            )

    return SIRStepResult(states=next_states.astype(np.int8, copy=False), events=events)
