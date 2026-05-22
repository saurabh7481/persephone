from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict


class DependencyWorkflowSolver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: StateDict, dt: float, bus: Any) -> tuple[StateDict, float]:
        del bus
        phase = float(state["phase"][0]) + dt
        service_risk = np.array(state["service_risk"], dtype=np.float64, copy=True)
        review_backlog = np.array(state["review_backlog"], dtype=np.float64, copy=True)
        edge_sources = np.array(state["edge_sources"], dtype=np.int64, copy=False)
        edge_targets = np.array(state["edge_targets"], dtype=np.int64, copy=False)
        edge_weights = np.array(state["edge_weights"], dtype=np.float64, copy=False)
        adjacency = np.zeros((len(service_risk), len(service_risk)), dtype=np.float64)
        adjacency[edge_sources, edge_targets] = edge_weights
        incoming = adjacency.T
        totals = incoming.sum(axis=1)
        upstream_pressure = np.divide(
            incoming @ service_risk,
            totals,
            out=np.zeros_like(service_risk),
            where=totals > 0,
        )
        oscillation = 0.75 + 0.25 * np.cos(phase)
        next_backlog = np.clip(
            0.78 * review_backlog + 4.0 * upstream_pressure * oscillation + np.array([0.2, 0.4, 0.5, 0.3, 0.6]),
            0.0,
            15.0,
        )
        normalized_backlog = next_backlog / 15.0
        next_risk = np.clip(
            0.52 * service_risk + 0.28 * upstream_pressure + 0.2 * normalized_backlog,
            0.03,
            0.99,
        )
        next_state = dict(state)
        next_state["service_risk"] = next_risk
        next_state["review_backlog"] = next_backlog
        next_state["risk_velocity"] = next_risk - service_risk
        next_state["phase"] = np.array([phase], dtype=np.float64)
        return next_state, dt
