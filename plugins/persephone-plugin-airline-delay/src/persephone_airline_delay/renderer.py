from __future__ import annotations

from importlib.resources import files
from typing import Any

import numpy as np
from persephone_sdk.plugin import Renderer
from persephone_sdk.types import GraphEdge, GraphNode, SimulationFrame, StateDict

from persephone_airline_delay.dataset import load_airport_graph
from persephone_airline_delay.model import status_label

_DATA: Any = None  # cached airport metadata (iata + names)


def _airport_meta() -> tuple[tuple[str, ...], tuple[str, ...]]:
    global _DATA
    if _DATA is None:
        data = load_airport_graph(
            files("persephone_airline_delay").joinpath("data/airports.csv"),
            files("persephone_airline_delay").joinpath("data/routes.csv"),
        )
        _DATA = (data.iata, data.names)
    return _DATA  # type: ignore[return-value]


class AirlineDelayRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {
            "type": "graph_airline_delay",
            "state_channel": "status",
            "edge_channels": {
                "source": "edge_sources",
                "target": "edge_targets",
                "weight": "edge_weights",
            },
            "charts": ["disrupted_airports", "total_delay_minutes", "cascade_reach"],
        }

    def frame(
        self,
        state: StateDict,
        *,
        t: float,
        run_id: str,
        solver_id: str,
        tick: int,
        source: str = "live",
    ) -> list[SimulationFrame]:
        delay = np.asarray(state["delay_minutes"], dtype=np.float64)
        status = np.asarray(state["status"], dtype=np.int8)
        lats = np.asarray(state["lats"], dtype=np.float64)
        lons = np.asarray(state["lons"], dtype=np.float64)
        edge_sources = np.asarray(state["edge_sources"], dtype=np.int64)
        edge_targets = np.asarray(state["edge_targets"], dtype=np.int64)
        edge_weights = np.asarray(state["edge_weights"], dtype=np.float64)
        iata_codes, names = _airport_meta()

        nodes: list[GraphNode] = [
            {
                "id": iata_codes[i],
                "label": iata_codes[i],
                "group": names[i],
                "state": status_label(int(status[i])),
                "lat": float(lats[i]),
                "lon": float(lons[i]),
                "metrics": {"delay_minutes": float(delay[i])},
            }
            for i in range(len(iata_codes))
        ]
        edges: list[GraphEdge] = [
            {
                "source": iata_codes[int(edge_sources[j])],
                "target": iata_codes[int(edge_targets[j])],
                "weight": float(edge_weights[j]),
                "directed": False,
            }
            for j in range(len(edge_sources))
        ]
        return [
            {
                "kind": "graph",
                "run_id": run_id,
                "frame_id": f"{solver_id}:graph:{tick:06d}",
                "t": t,
                "tick": tick,
                "solver_id": solver_id,
                "source": source,
                "schema_version": 1,
                "nodes": nodes,
                "edges": edges,
                "visualization": {
                    "coordinate_system": "geo",
                    "preferred_view": "map_network",
                    "node_state_field": "state",
                    "legend": {
                        "state": {
                            "normal": "No significant delay",
                            "minor": "15–45 min delay",
                            "major": "45–120 min delay",
                            "disrupted": ">120 min delay",
                        }
                    },
                },
            }
        ]
