from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict

from persephone_market_stress.model import (
    base_risk_vector,
    beta_vector,
    edge_sources_array,
    edge_targets_array,
    edge_weights_array,
)


class MarketStressWorld(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        edge_count = len(edge_sources_array())
        node_count = len(base_risk_vector())
        return {
            "risk_scores": (node_count,),
            "stress_velocity": (node_count,),
            "sector_beta": (node_count,),
            "phase": (1,),
            "edge_sources": (edge_count,),
            "edge_targets": (edge_count,),
            "edge_weights": (edge_count,),
        }

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        del seed
        stress_bias = float(params.get("stress_bias", 0.0))
        correlation_scale = float(params.get("correlation_scale", 1.0))
        risk_scores = np.clip(base_risk_vector() + stress_bias, 0.05, 0.95)
        self._initial = {
            "risk_scores": risk_scores,
            "stress_velocity": np.zeros_like(risk_scores),
            "sector_beta": beta_vector(),
            "phase": np.array([0.0], dtype=np.float64),
            "edge_sources": edge_sources_array(),
            "edge_targets": edge_targets_array(),
            "edge_weights": edge_weights_array() * correlation_scale,
        }
        return {key: value.copy() for key, value in self._initial.items()}

    def reset(self) -> StateDict:
        assert self._initial is not None
        return {key: value.copy() for key, value in self._initial.items()}
