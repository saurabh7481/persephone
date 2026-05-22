from __future__ import annotations

import numpy as np
from persephone_sdk.plugin import Observer
from persephone_sdk.types import MetricRecord, StateDict


class AirlineDelayObserver(Observer):
    def __init__(self) -> None:
        self._ever_delayed: set[int] = set()

    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        delay = state["delay_minutes"]
        status = state["status"]

        delayed_mask = delay >= 15.0
        self._ever_delayed.update(int(i) for i in np.flatnonzero(delayed_mask))

        return [
            _m(run_id, "delayed_airports", float(np.sum(delayed_mask)), t),
            _m(run_id, "disrupted_airports", float(np.sum(status == 3)), t),
            _m(run_id, "total_delay_minutes", float(np.sum(delay)), t),
            _m(run_id, "max_delay_minutes", float(np.max(delay)), t),
            _m(run_id, "cascade_reach", float(len(self._ever_delayed)), t),
        ]


def _m(run_id: str, metric: str, value: float, t: float) -> MetricRecord:
    return {"run_id": run_id, "metric": metric, "value": value, "t": t, "tags": {}}
