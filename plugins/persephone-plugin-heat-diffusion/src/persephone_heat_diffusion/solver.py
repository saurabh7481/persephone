from __future__ import annotations

import numpy as np
from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict


class HeatSolver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 0.1

    @property
    def is_stochastic(self) -> bool:
        return False

    def step(self, state: StateDict, dt: float, bus: object) -> tuple[StateDict, float]:
        temperature = state["temperature"]
        alpha = float(state["alpha"])
        dx = float(state["dx"])
        dy = float(state["dy"])
        max_dt = _cfl_limit(alpha=alpha, dx=dx, dy=dy)
        if dt - max_dt > 1e-12:
            raise ValueError(f"CFL stability violation: dt={dt:g} exceeds {max_dt:g}")

        padded = np.pad(temperature, pad_width=1, mode="edge")
        center = padded[1:-1, 1:-1]
        laplacian_x = (padded[1:-1, 2:] - 2.0 * center + padded[1:-1, :-2]) / (dx * dx)
        laplacian_y = (padded[2:, 1:-1] - 2.0 * center + padded[:-2, 1:-1]) / (dy * dy)
        next_temperature = temperature + alpha * dt * (laplacian_x + laplacian_y)

        next_state = dict(state)
        next_state["temperature"] = next_temperature
        if hasattr(bus, "write"):
            bus.write("temperature", next_temperature, solver_id="heat_diffusion", tick=0)
        return next_state, dt


def _cfl_limit(*, alpha: float, dx: float, dy: float) -> float:
    return (dx * dx * dy * dy) / (2.0 * alpha * (dx * dx + dy * dy))
