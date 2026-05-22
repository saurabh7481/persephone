from __future__ import annotations

import numpy as np
from persephone_sdk.plugin import Observer
from persephone_sdk.types import MetricRecord, StateDict

from persephone_river_flood.model import WARNING, WATCH


class RiverFloodObserver(Observer):
    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        flow = state["flow_cms"]
        flood_status = state["flood_status"]
        normal_flow = state["normal_flow_cms"]
        river_km = state["river_km"]

        at_watch = flood_status >= WATCH
        at_warning = flood_status >= WARNING

        # flood_front_km: farthest downstream station at warning or flood
        warning_km = river_km[at_warning]
        flood_front_km = float(np.max(warning_km)) if len(warning_km) > 0 else 0.0

        excess = np.maximum(flow - normal_flow, 0.0)

        return [
            _m(run_id, "stations_flooding", float(np.sum(flood_status == 3)), t),
            _m(run_id, "stations_watch", float(np.sum(at_watch)), t),
            _m(run_id, "total_excess_flow_cms", float(np.sum(excess)), t),
            _m(run_id, "peak_flow_cms", float(np.max(flow)), t),
            _m(run_id, "flood_front_km", flood_front_km, t),
        ]


def _m(run_id: str, metric: str, value: float, t: float) -> MetricRecord:
    return {"run_id": run_id, "metric": metric, "value": value, "t": t, "tags": {}}
