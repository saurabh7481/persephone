from __future__ import annotations

from importlib.resources import files
from typing import Any

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict

from persephone_river_flood.dataset import load_flood_network
from persephone_river_flood.model import NORMAL, steady_state_storage


class RiverFloodWorld(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        if self._initial is None:
            return {"storage_m3": (0,)}
        return {k: v.shape for k, v in self._initial.items()}

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        gauges_path = params.get(
            "gauges_path",
            str(files("persephone_river_flood").joinpath("data/gauges.csv")),
        )
        network_path = params.get(
            "network_path",
            str(files("persephone_river_flood").joinpath("data/network.csv")),
        )
        data = load_flood_network(gauges_path, network_path)
        routing_k = float(params.get("routing_k", 0.35))

        storage_m3 = steady_state_storage(data.normal_flow_cms, routing_k)
        flow_cms = data.normal_flow_cms.copy()
        flood_status = np.full(len(data.names), NORMAL, dtype=np.int8)
        edge_weights = 1.0 / np.maximum(data.travel_time_hours, 1.0)

        # Compute local base inflow for each station to sustain steady state flow
        base_inflow_cms = data.normal_flow_cms.copy()
        for i in range(len(data.upstream_ids)):
            src = int(data.upstream_ids[i])
            tgt = int(data.downstream_ids[i])
            w = float(edge_weights[i])
            base_inflow_cms[tgt] -= data.normal_flow_cms[src] * w
        base_inflow_cms = np.maximum(base_inflow_cms, 0.0)

        self._initial = {
            "storage_m3": storage_m3,
            "flow_cms": flow_cms,
            "flood_status": flood_status,
            "flood_stage_cms": data.flood_stage_cms.copy(),
            "normal_flow_cms": data.normal_flow_cms.copy(),
            "base_inflow_cms": base_inflow_cms,
            "river_km": data.river_km.copy(),
            "upstream_ids": data.upstream_ids.copy(),
            "downstream_ids": data.downstream_ids.copy(),
            "edge_weights": edge_weights,
            "lats": data.lats.copy(),
            "lons": data.lons.copy(),
            "routing_k": np.array([routing_k]),
            "precipitation_cms": np.array([float(params.get("precipitation_cms", 500.0))]),
            "precip_duration_hours": np.array([int(params.get("precipitation_duration_hours", 24))], dtype=np.int64),
            "event_preset": np.array([0], dtype=np.int64),  # stored as tick counter; preset resolved in solver
        }

        # store injection mask
        from persephone_river_flood.dataset import injection_station_ids
        preset = str(params.get("event_preset", "spring_snowmelt"))
        custom = list(params.get("custom_injection_stations", []))
        injection_ids = injection_station_ids(preset, custom)
        injection_mask = np.zeros(len(data.names), dtype=np.float64)
        injection_mask[injection_ids] = 1.0
        self._initial["injection_mask"] = injection_mask

        return {k: v.copy() for k, v in self._initial.items()}

    def reset(self) -> StateDict:
        if self._initial is None:
            raise RuntimeError("World not initialised — call init() first")
        return {k: v.copy() for k, v in self._initial.items()}
