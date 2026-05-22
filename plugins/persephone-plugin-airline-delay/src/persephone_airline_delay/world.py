from __future__ import annotations

from importlib.resources import files
from typing import Any

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict

from persephone_airline_delay.dataset import load_airport_graph
from persephone_airline_delay.model import classify_status


class AirlineDelayWorld(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        if self._initial is None:
            return {"delay_minutes": (0,)}
        return {k: v.shape for k, v in self._initial.items()}

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        airports_path = params.get(
            "airports_path",
            str(files("persephone_airline_delay").joinpath("data/airports.csv")),
        )
        routes_path = params.get(
            "routes_path",
            str(files("persephone_airline_delay").joinpath("data/routes.csv")),
        )
        data = load_airport_graph(airports_path, routes_path)
        n = len(data.iata)

        delay_minutes = np.zeros(n, dtype=np.float64)
        initial_airports: list[str] = params.get("initial_airports", ["JFK", "LHR", "DXB"])
        initial_delay = float(params.get("initial_delay_minutes", 180.0))
        for iata in initial_airports:
            idx = data.iata_to_index.get(iata)
            if idx is not None:
                delay_minutes[idx] = initial_delay

        self._initial = {
            "delay_minutes": delay_minutes,
            "status": classify_status(delay_minutes),
            "edge_sources": data.edge_sources.copy(),
            "edge_targets": data.edge_targets.copy(),
            "edge_weights": data.edge_weights.copy(),
            "lats": data.lats.copy(),
            "lons": data.lons.copy(),
            "route_counts": data.route_counts.copy(),
            "propagation_factor": np.array([float(params.get("propagation_factor", 0.3))]),
            "recovery_rate": np.array([float(params.get("recovery_rate", 0.15))]),
        }
        return {k: v.copy() for k, v in self._initial.items()}

    def reset(self) -> StateDict:
        if self._initial is None:
            raise RuntimeError("World not initialised — call init() first")
        return {k: v.copy() for k, v in self._initial.items()}
