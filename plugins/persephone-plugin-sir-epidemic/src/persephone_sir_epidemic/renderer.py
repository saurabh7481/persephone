from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import Renderer


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
