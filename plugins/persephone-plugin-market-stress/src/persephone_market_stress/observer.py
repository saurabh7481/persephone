from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Observer
from persephone_sdk.types import EventRecord, MetricRecord, SimulationFrame, StateDict

from persephone_market_stress.model import SECTORS, sector_ids, stress_state


class MarketStressObserver(Observer):
    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        risk_scores = np.array(state["risk_scores"], dtype=np.float64, copy=False)
        edge_weights = np.array(state["edge_weights"], dtype=np.float64, copy=False)
        return [
            _metric(run_id, "portfolio_stress_index", float(risk_scores.mean() * 100.0), t),
            _metric(run_id, "correlation_pressure", float(edge_weights.mean() * 100.0), t),
            _metric(run_id, "active_shocks", float(np.count_nonzero(risk_scores >= 0.72)), t),
            _metric(run_id, "dispersion_index", float(np.std(risk_scores) * 100.0), t),
        ]

    def explain(
        self,
        state: StateDict,
        *,
        t: float,
        tick: int,
        run_id: str,
        solver_id: str,
        metrics: list[MetricRecord],
        events: list[EventRecord],
        frames: list[SimulationFrame],
    ) -> list[dict[str, Any]]:
        del tick, solver_id, events
        risk_scores = np.array(state["risk_scores"], dtype=np.float64, copy=False)
        stress_values = {metric["metric"]: float(metric["value"]) for metric in metrics}
        hottest_index = int(np.argmax(risk_scores))
        hottest_sector = SECTORS[hottest_index]
        frame_id = str(frames[0]["frame_id"]) if frames else None
        packets: list[dict[str, Any]] = [
            {
                "scope": "run",
                "facts": [
                    {
                        "kind": "trend",
                        "title": "Market stress remains clustered",
                        "summary": (
                            f"{hottest_sector['label']} is leading the tape while stress breadth sits at "
                            f"{stress_values['active_shocks']:.0f} sectors."
                        ),
                        "severity": "warning"
                        if stress_values["portfolio_stress_index"] >= 55
                        else "notice",
                        "evidence": [
                            {
                                "label": "portfolio_stress_index",
                                "value": round(stress_values["portfolio_stress_index"], 2),
                                "unit": "idx",
                            },
                            {
                                "label": "correlation_pressure",
                                "value": round(stress_values["correlation_pressure"], 2),
                                "unit": "idx",
                            },
                        ],
                        "related_ids": sector_ids(),
                        "t": t,
                    }
                ],
            }
        ]
        if frame_id is not None:
            packets.append(
                {
                    "scope": "frame",
                    "frame_id": frame_id,
                    "facts": [
                        {
                            "kind": "hotspot",
                            "title": f"{hottest_sector['label']} is the current hotspot",
                            "summary": (
                                f"Risk climbed to {risk_scores[hottest_index]:.2f} in the "
                                f"{hottest_sector['label']} sleeve."
                            ),
                            "severity": "critical"
                            if risk_scores[hottest_index] >= 0.8
                            else "warning",
                            "evidence": [
                                {
                                    "label": "sector",
                                    "value": hottest_sector["label"],
                                },
                                {
                                    "label": "stress",
                                    "value": round(float(risk_scores[hottest_index]), 3),
                                    "unit": "score",
                                },
                            ],
                            "related_ids": [hottest_sector["id"]],
                            "t": t,
                        }
                    ],
                }
            )
        for index, sector in enumerate(SECTORS):
            state_name = stress_state(float(risk_scores[index]))
            packets.append(
                {
                    "scope": "selection",
                    "selection_id": sector["id"],
                    "facts": [
                        {
                            "kind": "selection",
                            "title": f"{sector['label']} sector is {state_name}",
                            "summary": (
                                f"{sector['mandate']} now carries a stress score of "
                                f"{risk_scores[index]:.2f}."
                            ),
                            "severity": "warning" if state_name != "stable" else "info",
                            "evidence": [
                                {
                                    "label": "liquidity_bucket",
                                    "value": sector["liquidity_bucket"],
                                },
                                {
                                    "label": "stress",
                                    "value": round(float(risk_scores[index]), 3),
                                    "unit": "score",
                                },
                            ],
                            "related_ids": [sector["id"]],
                            "t": t,
                        }
                    ],
                }
            )
        return packets


def _metric(run_id: str, name: str, value: float, t: float) -> MetricRecord:
    return {"run_id": run_id, "metric": name, "value": float(value), "t": t, "tags": {}}
