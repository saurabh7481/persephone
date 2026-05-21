from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import Renderer


class HeatRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "name": "temperature",
                    "kind": "heatmap",
                    "units": "temperature",
                    "color_scale": "viridis",
                }
            ]
        }
