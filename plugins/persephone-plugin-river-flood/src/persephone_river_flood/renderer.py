from __future__ import annotations

from importlib.resources import files
from typing import Any

import numpy as np
from persephone_sdk.plugin import Renderer
from persephone_sdk.types import GraphEdge, GraphNode, SimulationFrame, StateDict

from persephone_river_flood.dataset import load_flood_network
from persephone_river_flood.model import flood_status_label

_NETWORK: Any = None


def _network_meta():
    global _NETWORK
    if _NETWORK is None:
        _NETWORK = load_flood_network(
            files("persephone_river_flood").joinpath("data/gauges.csv"),
            files("persephone_river_flood").joinpath("data/network.csv"),
        )
    return _NETWORK


class RiverFloodRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {
            "type": "graph_river_flood",
            "state_channel": "flood_status",
            "edge_channels": {
                "source": "upstream_ids",
                "target": "downstream_ids",
                "weight": "edge_weights",
            },
            "charts": ["stations_flooding", "total_excess_flow_cms", "flood_front_km"],
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
        data = _network_meta()
        flow = np.asarray(state["flow_cms"], dtype=np.float64)
        flood_status = np.asarray(state["flood_status"], dtype=np.int8)
        lats = np.asarray(state["lats"], dtype=np.float64)
        lons = np.asarray(state["lons"], dtype=np.float64)
        upstream_ids = np.asarray(state["upstream_ids"], dtype=np.int64)
        downstream_ids = np.asarray(state["downstream_ids"], dtype=np.int64)
        edge_weights = np.asarray(state["edge_weights"], dtype=np.float64)

        nodes: list[GraphNode] = [
            {
                "id": str(i),
                "label": data.names[i],
                "group": data.states[i],
                "state": flood_status_label(int(flood_status[i])),
                "lat": float(lats[i]),
                "lon": float(lons[i]),
                "metrics": {"flow_cms": float(flow[i])},
            }
            for i in range(len(data.names))
        ]
        edges: list[GraphEdge] = [
            {
                "source": str(int(upstream_ids[j])),
                "target": str(int(downstream_ids[j])),
                "weight": float(edge_weights[j]),
                "directed": True,
                "kind": "river_reach",
            }
            for j in range(len(upstream_ids))
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
                            "normal": "Below watch stage",
                            "watch": "70% of flood stage",
                            "warning": "90% of flood stage",
                            "flood": "At or above flood stage",
                        }
                    },
                },
            }
        ]
