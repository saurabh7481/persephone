from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import Renderer
from persephone_sdk.types import GraphEdge, GraphNode, SimulationFrame, StateDict


class SIRRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {
            "type": "graph_sir",
            "state_channel": "states",
            "edge_channels": {
                "source": "edge_sources",
                "target": "edge_targets",
                "weight": "edge_weights",
            },
            "charts": ["susceptible_count", "infected_count", "recovered_count"],
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
        states = state["states"]
        edge_sources = state["edge_sources"]
        edge_targets = state["edge_targets"]
        edge_weights = state["edge_weights"]
        nodes: list[GraphNode] = [
            {"id": str(index), "state": _state_name(int(value))}
            for index, value in enumerate(states.tolist())
        ]
        edges: list[GraphEdge] = [
            {
                "source": str(int(edge_sources[index])),
                "target": str(int(edge_targets[index])),
                "weight": float(edge_weights[index]),
            }
            for index in range(len(edge_sources))
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
                "visualization": {"kind": "network", "node_state_field": "state"},
            }
        ]


def _state_name(value: int) -> str:
    return {0: "state_0", 1: "state_1", 2: "state_2"}.get(value, f"state_{value}")
