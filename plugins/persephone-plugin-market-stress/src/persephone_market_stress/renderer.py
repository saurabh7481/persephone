from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Renderer
from persephone_sdk.types import GraphEdge, GraphNode, SimulationFrame, StateDict

from persephone_market_stress.model import SECTORS, stress_state


class MarketStressRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {
            "type": "graph_market_stress",
            "state_channel": "risk_scores",
            "edge_channels": {
                "source": "edge_sources",
                "target": "edge_targets",
                "weight": "edge_weights",
            },
            "charts": [
                "portfolio_stress_index",
                "correlation_pressure",
                "active_shocks",
                "dispersion_index",
            ],
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
        risk_scores = np.array(state["risk_scores"], dtype=np.float64, copy=False)
        sector_beta = np.array(state["sector_beta"], dtype=np.float64, copy=False)
        stress_velocity = np.array(state["stress_velocity"], dtype=np.float64, copy=False)
        edge_sources = np.array(state["edge_sources"], dtype=np.int64, copy=False)
        edge_targets = np.array(state["edge_targets"], dtype=np.int64, copy=False)
        edge_weights = np.array(state["edge_weights"], dtype=np.float64, copy=False)
        nodes: list[GraphNode] = [
            {
                "id": sector["id"],
                "label": sector["label"],
                "group": sector["group"],
                "state": stress_state(float(risk_scores[index])),
                "metrics": {
                    "stress": float(risk_scores[index]),
                    "beta": float(sector_beta[index]),
                    "delta": float(stress_velocity[index]),
                },
                "attrs": {
                    "mandate": sector["mandate"],
                    "liquidity_bucket": sector["liquidity_bucket"],
                },
            }
            for index, sector in enumerate(SECTORS)
        ]
        edges: list[GraphEdge] = [
            {
                "source": SECTORS[int(edge_sources[index])]["id"],
                "target": SECTORS[int(edge_targets[index])]["id"],
                "weight": float(edge_weights[index]),
                "kind": "correlation",
                "directed": False,
                "attrs": {
                    "strength_bucket": "tight" if edge_weights[index] >= 0.7 else "moderate",
                },
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
                "visualization": {
                    "layout_hint": "radial",
                    "preferred_view": "matrix",
                    "density_hint": "dense",
                    "selection_schema": {"type": "node", "entity_type": "sector"},
                    "legend": {
                        "state": {
                            "stable": "Contained stress",
                            "watch": "Stress building",
                            "stressed": "Stress regime active",
                        }
                    },
                },
            }
        ]
