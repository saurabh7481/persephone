from __future__ import annotations

import numpy as np
from persephone_sdk.plugin import Observer
from persephone_sdk.types import MetricRecord, StateDict

from persephone_us_county_epidemic.model import INFECTED, RECOVERED, SUSCEPTIBLE


class USCountyObserver(Observer):
    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        states = state["states"]
        infected = int(np.count_nonzero(states == INFECTED))
        new_infections = int(state.get("last_new_infections", np.array([0]))[0])
        return [
            _metric(run_id, "susceptible_count", int(np.count_nonzero(states == SUSCEPTIBLE)), t),
            _metric(run_id, "infected_count", infected, t),
            _metric(run_id, "recovered_count", int(np.count_nonzero(states == RECOVERED)), t),
            _metric(run_id, "new_infections", new_infections, t),
            _metric(
                run_id,
                "new_recoveries",
                int(state.get("last_new_recoveries", np.array([0]))[0]),
                t,
            ),
            _metric(run_id, "r_effective_estimate", _r_effective(new_infections, infected), t),
        ]


def _metric(run_id: str, name: str, value: float, t: float) -> MetricRecord:
    return {"run_id": run_id, "metric": name, "value": float(value), "t": t, "tags": {}}


def _r_effective(new_infections: int, infected: int) -> float:
    if infected == 0:
        return 0.0
    return float(new_infections / infected)
