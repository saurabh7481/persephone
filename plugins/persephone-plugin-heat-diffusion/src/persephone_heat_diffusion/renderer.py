from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import Renderer
from persephone_sdk.types import SimulationFrame, StateDict


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
        field = state["temperature"]
        return [
            {
                "kind": "field",
                "run_id": run_id,
                "frame_id": f"{solver_id}:temperature:{tick:06d}",
                "t": t,
                "tick": tick,
                "solver_id": solver_id,
                "source": source,
                "schema_version": 1,
                "field": "temperature",
                "shape": (int(field.shape[0]), int(field.shape[1])),
                "dtype": str(field.dtype),
                "bounds": {"min": float(field.min()), "max": float(field.max())},
                "units": "temperature",
                "visualization": {"kind": "heatmap", "color_scale": "viridis"},
                "values": [float(value) for value in field.reshape(-1)],
            }
        ]
