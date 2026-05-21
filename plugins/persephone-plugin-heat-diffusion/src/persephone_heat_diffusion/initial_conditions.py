from __future__ import annotations

from pathlib import Path

import numpy as np


def write_initial_condition(
    output: str | Path,
    *,
    width: int,
    height: int,
    seed: int,
    ambient_temperature: float = 0.0,
    hotspot_temperature: float = 100.0,
) -> Path:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width]
    center_x = (width - 1) / 2.0 + rng.uniform(-0.5, 0.5)
    center_y = (height - 1) / 2.0 + rng.uniform(-0.5, 0.5)
    sigma = max(width, height) / 6.0
    field = ambient_temperature + hotspot_temperature * np.exp(
        -(((x - center_x) ** 2 + (y - center_y) ** 2) / (2 * sigma**2))
    )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, field.astype(np.float64))
    return output_path
