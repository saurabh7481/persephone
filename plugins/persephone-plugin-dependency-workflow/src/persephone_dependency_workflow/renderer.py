from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Renderer
from persephone_sdk.types import GraphEdge, GraphNode, SimulationFrame, StateDict

from persephone_dependency_workflow.model import SERVICES, workflow_state


class DependencyWorkflowRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {
            "type": "graph_dependency_workflow",
            "state_channel": "service_risk",
            "edge_channels": {
                "source": "edge_sources",
                "target": "edge_targets",
                "weight": "edge_weights",
            },
            "charts": [
                "delivery_risk_index",
                "blocked_items",
                "review_backlog",
                "critical_path_pressure",
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
        service_risk = np.array(state["service_risk"], dtype=np.float64, copy=False)
        review_backlog = np.array(state["review_backlog"], dtype=np.float64, copy=False)
        risk_velocity = np.array(state["risk_velocity"], dtype=np.float64, copy=False)
        edge_sources = np.array(state["edge_sources"], dtype=np.int64, copy=False)
        edge_targets = np.array(state["edge_targets"], dtype=np.int64, copy=False)
        edge_weights = np.array(state["edge_weights"], dtype=np.float64, copy=False)
        nodes: list[GraphNode] = [
            {
                "id": service["id"],
                "label": service["label"],
                "group": service["group"],
                "state": workflow_state(float(service_risk[index])),
                "metrics": {
                    "service_risk": float(service_risk[index]),
                    "review_backlog": float(review_backlog[index]),
                    "risk_delta": float(risk_velocity[index]),
                },
                "attrs": {
                    "owner": service["owner"],
                    "tier": service["tier"],
                },
            }
            for index, service in enumerate(SERVICES)
        ]
        edges: list[GraphEdge] = [
            {
                "source": SERVICES[int(edge_sources[index])]["id"],
                "target": SERVICES[int(edge_targets[index])]["id"],
                "weight": float(edge_weights[index]),
                "kind": "depends_on",
                "directed": True,
                "attrs": {
                    "critical_path": bool(edge_weights[index] >= 0.8),
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
                    "layout_hint": "hierarchy",
                    "preferred_view": "hierarchy",
                    "selection_schema": {"type": "node", "entity_type": "service"},
                    "legend": {
                        "state": {
                            "healthy": "Delivery flow is healthy",
                            "watch": "Pressure is building",
                            "blocked": "Critical path blocker",
                        }
                    },
                },
            }
        ]
