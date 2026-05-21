from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray

from persephone.solvers.graph import ContactGraph

SUSCEPTIBLE = 0
INFECTED = 1
RECOVERED = 2


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
