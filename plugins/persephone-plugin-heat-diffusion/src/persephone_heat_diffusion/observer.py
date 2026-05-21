from __future__ import annotations

import numpy as np
from persephone_sdk.plugin import Observer
from persephone_sdk.types import MetricRecord, StateDict


class HeatObserver(Observer):
    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        temperature = state["temperature"]
        center = temperature[temperature.shape[0] // 2, temperature.shape[1] // 2]
        return [
            _metric(run_id, "temperature_min", float(np.min(temperature)), t),
            _metric(run_id, "temperature_max", float(np.max(temperature)), t),
            _metric(run_id, "temperature_mean", float(np.mean(temperature)), t),
            _metric(run_id, "total_heat", float(np.sum(temperature)), t),
            _metric(run_id, "center_temperature", float(center), t),
        ]


def _metric(run_id: str, name: str, value: float, t: float) -> MetricRecord:
    return {
        "run_id": run_id,
        "solver_id": "heat_diffusion",
        "metric": name,
        "value": value,
        "t": t,
        "tags": {},
    }
