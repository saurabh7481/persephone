from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict

from persephone_river_flood.model import route_step


class RiverFloodSolver(Solver):
    def __init__(self) -> None:
        self._tick = 0

    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: StateDict, dt: float, bus: Any) -> tuple[StateDict, float]:
        precip_duration = int(state["precip_duration_hours"][0])
        precip_cms = float(state["precipitation_cms"][0])
        routing_k = float(state["routing_k"][0])

        precip_input = state["base_inflow_cms"].copy()
        if self._tick < precip_duration:
            precip_input += state["injection_mask"] * precip_cms

        new_storage, new_flow, new_status = route_step(
            state["storage_m3"],
            state["flow_cms"],
            state["upstream_ids"],
            state["downstream_ids"],
            state["edge_weights"],
            precip_input,
            state["flood_stage_cms"],
            state["normal_flow_cms"],
            routing_k,
        )

        new_state = {k: v.copy() for k, v in state.items()}
        new_state["storage_m3"] = new_storage
        new_state["flow_cms"] = new_flow
        new_state["flood_status"] = new_status
        self._tick += 1
        return new_state, dt
