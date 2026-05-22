from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict

from persephone_dependency_workflow.model import (
    base_backlog_vector,
    base_risk_vector,
    edge_sources_array,
    edge_targets_array,
    edge_weights_array,
)


class DependencyWorkflowWorld(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        edge_count = len(edge_sources_array())
        node_count = len(base_risk_vector())
        return {
            "service_risk": (node_count,),
            "review_backlog": (node_count,),
            "risk_velocity": (node_count,),
            "phase": (1,),
            "edge_sources": (edge_count,),
            "edge_targets": (edge_count,),
            "edge_weights": (edge_count,),
        }

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        del seed
        risk_bias = float(params.get("risk_bias", 0.0))
        backlog_bias = float(params.get("backlog_bias", 0.0))
        self._initial = {
            "service_risk": np.clip(base_risk_vector() + risk_bias, 0.02, 0.98),
            "review_backlog": np.clip(base_backlog_vector() + backlog_bias, 0.0, None),
            "risk_velocity": np.zeros_like(base_risk_vector()),
            "phase": np.array([0.0], dtype=np.float64),
            "edge_sources": edge_sources_array(),
            "edge_targets": edge_targets_array(),
            "edge_weights": edge_weights_array(),
        }
        return {key: value.copy() for key, value in self._initial.items()}

    def reset(self) -> StateDict:
        assert self._initial is not None
        return {key: value.copy() for key, value in self._initial.items()}
