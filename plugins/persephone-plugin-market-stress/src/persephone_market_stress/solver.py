from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict


class MarketStressSolver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: StateDict, dt: float, bus: Any) -> tuple[StateDict, float]:
        del bus
        phase = float(state["phase"][0]) + dt
        risk = np.array(state["risk_scores"], dtype=np.float64, copy=True)
        edge_sources = np.array(state["edge_sources"], dtype=np.int64, copy=False)
        edge_targets = np.array(state["edge_targets"], dtype=np.int64, copy=False)
        edge_weights = np.array(state["edge_weights"], dtype=np.float64, copy=False)
        adjacency = np.zeros((len(risk), len(risk)), dtype=np.float64)
        adjacency[edge_sources, edge_targets] = edge_weights
        adjacency[edge_targets, edge_sources] = edge_weights
        totals = adjacency.sum(axis=1)
        influence = np.divide(
            adjacency @ risk,
            totals,
            out=np.zeros_like(risk),
            where=totals > 0,
        )
        rotation = np.array([0.06, -0.01, 0.05, 0.03], dtype=np.float64)
        oscillation = 1.0 + 0.35 * np.sin(phase)
        next_risk = np.clip(0.58 * risk + 0.28 * influence + rotation * oscillation, 0.04, 0.98)
        next_state = dict(state)
        next_state["risk_scores"] = next_risk
        next_state["stress_velocity"] = next_risk - risk
        next_state["phase"] = np.array([phase], dtype=np.float64)
        return next_state, dt
