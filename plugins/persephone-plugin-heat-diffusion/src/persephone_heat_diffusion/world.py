from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict


class HeatWorld(World):
    def __init__(self) -> None:
        self._initial_state: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        return {"temperature": (12, 12)}

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        width = int(params.get("width", 12))
        height = int(params.get("height", 12))
        if width < 3 or height < 3:
            raise ValueError("Heat diffusion grid requires width and height >= 3")

        temperature = _initial_temperature(params, width=width, height=height, seed=seed)
        state: StateDict = {
            "temperature": temperature.astype(np.float64),
            "alpha": np.array(float(params.get("alpha", 0.2)), dtype=np.float64),
            "dx": np.array(float(params.get("dx", 1.0)), dtype=np.float64),
            "dy": np.array(float(params.get("dy", 1.0)), dtype=np.float64),
        }
        self._initial_state = {key: value.copy() for key, value in state.items()}
        return state

    def reset(self) -> StateDict:
        if self._initial_state is None:
            return self.init({}, seed=0)
        return {key: value.copy() for key, value in self._initial_state.items()}


def _initial_temperature(
    params: dict[str, Any],
    *,
    width: int,
    height: int,
    seed: int,
) -> np.ndarray[Any, Any]:
    path = params.get("initial_condition_path")
    if path is not None:
        loaded = cast(np.ndarray[Any, Any], np.load(Path(str(path))))
        if loaded.shape != (height, width):
            raise ValueError(
                "Initial condition shape must match grid: "
                f"expected {(height, width)}, got {loaded.shape}"
            )
        return loaded.astype(np.float64)

    ambient = float(params.get("ambient_temperature", 0.0))
    hotspot = float(params.get("hotspot_temperature", 100.0))
    field = np.full((height, width), ambient, dtype=np.float64)
    condition = str(params.get("initial_condition", "center_hotspot"))
    if condition == "center_hotspot":
        field[height // 2, width // 2] = hotspot
    elif condition == "gaussian":
        rng = np.random.default_rng(seed)
        center_x = (width - 1) / 2.0 + rng.uniform(-0.25, 0.25)
        center_y = (height - 1) / 2.0 + rng.uniform(-0.25, 0.25)
        y, x = np.mgrid[0:height, 0:width]
        sigma = max(width, height) / 6.0
        field += hotspot * np.exp(-(((x - center_x) ** 2 + (y - center_y) ** 2) / (2 * sigma**2)))
    elif condition != "uniform":
        raise ValueError(f"Unknown heat initial_condition: {condition}")
    return field
