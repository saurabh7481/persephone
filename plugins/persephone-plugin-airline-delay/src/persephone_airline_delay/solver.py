from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict

from persephone_airline_delay.model import classify_status, delay_step


class AirlineDelaySolver(Solver):
    def __init__(self) -> None:
        self._t = 0.0

    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: StateDict, dt: float, bus: Any) -> tuple[StateDict, float]:
        prev_delay = state["delay_minutes"]
        new_delay = delay_step(
            prev_delay,
            state["edge_sources"],
            state["edge_targets"],
            state["edge_weights"],
            float(state["propagation_factor"][0]),
            float(state["recovery_rate"][0]),
        )
        new_status = classify_status(new_delay)

        newly_disrupted = np.sum((new_status == 3) & (state["status"] != 3))
        newly_recovered = np.sum((new_status == 0) & (state["status"] != 0))

        new_state = {k: v.copy() for k, v in state.items()}
        new_state["delay_minutes"] = new_delay
        new_state["status"] = new_status
        new_state["newly_disrupted"] = np.array([int(newly_disrupted)], dtype=np.int64)
        new_state["newly_recovered"] = np.array([int(newly_recovered)], dtype=np.int64)
        self._t += dt
        return new_state, dt
