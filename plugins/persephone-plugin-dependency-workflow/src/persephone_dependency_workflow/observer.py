from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Observer
from persephone_sdk.types import EventRecord, MetricRecord, SimulationFrame, StateDict

from persephone_dependency_workflow.model import SERVICES, service_ids, workflow_state


class DependencyWorkflowObserver(Observer):
    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        service_risk = np.array(state["service_risk"], dtype=np.float64, copy=False)
        review_backlog = np.array(state["review_backlog"], dtype=np.float64, copy=False)
        return [
            _metric(run_id, "delivery_risk_index", float(service_risk.mean() * 100.0), t),
            _metric(run_id, "blocked_items", float(np.count_nonzero(service_risk >= 0.7)), t),
            _metric(run_id, "review_backlog", float(review_backlog.sum()), t),
            _metric(
                run_id,
                "critical_path_pressure",
                float((service_risk[[1, 2, 3]].mean() + review_backlog[[1, 2, 3]].mean() / 15.0) * 100.0),
                t,
            ),
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
        service_risk = np.array(state["service_risk"], dtype=np.float64, copy=False)
        review_backlog = np.array(state["review_backlog"], dtype=np.float64, copy=False)
        metric_values = {metric["metric"]: float(metric["value"]) for metric in metrics}
        hottest_index = int(np.argmax(service_risk))
        hottest_service = SERVICES[hottest_index]
        frame_id = str(frames[0]["frame_id"]) if frames else None
        packets: list[dict[str, Any]] = [
            {
                "scope": "run",
                "facts": [
                    {
                        "kind": "trend",
                        "title": "Delivery risk is clustering on the critical path",
                        "summary": (
                            f"Workflow pressure sits at {metric_values['delivery_risk_index']:.1f} with "
                            f"{metric_values['blocked_items']:.0f} blocked services."
                        ),
                        "severity": "warning"
                        if metric_values["delivery_risk_index"] >= 50
                        else "notice",
                        "evidence": [
                            {
                                "label": "delivery_risk_index",
                                "value": round(metric_values["delivery_risk_index"], 2),
                                "unit": "idx",
                            },
                            {
                                "label": "review_backlog",
                                "value": round(metric_values["review_backlog"], 1),
                                "unit": "items",
                            },
                        ],
                        "related_ids": service_ids(),
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
                            "title": f"{hottest_service['label']} is the current blocker hotspot",
                            "summary": (
                                f"Risk reached {service_risk[hottest_index]:.2f} while backlog climbed to "
                                f"{review_backlog[hottest_index]:.1f} review items."
                            ),
                            "severity": "critical"
                            if service_risk[hottest_index] >= 0.78
                            else "warning",
                            "evidence": [
                                {"label": "owner", "value": hottest_service["owner"]},
                                {
                                    "label": "review_backlog",
                                    "value": round(float(review_backlog[hottest_index]), 1),
                                    "unit": "items",
                                },
                            ],
                            "related_ids": [hottest_service["id"]],
                            "t": t,
                        }
                    ],
                }
            )
        for index, service in enumerate(SERVICES):
            state_name = workflow_state(float(service_risk[index]))
            packets.append(
                {
                    "scope": "selection",
                    "selection_id": service["id"],
                    "facts": [
                        {
                            "kind": "selection",
                            "title": f"{service['label']} is {state_name}",
                            "summary": (
                                f"{service['owner']} owns this dependency, which is carrying "
                                f"{review_backlog[index]:.1f} queued reviews."
                            ),
                            "severity": "warning" if state_name != "healthy" else "info",
                            "evidence": [
                                {"label": "tier", "value": service["tier"]},
                                {
                                    "label": "service_risk",
                                    "value": round(float(service_risk[index]), 3),
                                    "unit": "score",
                                },
                            ],
                            "related_ids": [service["id"]],
                            "t": t,
                        }
                    ],
                }
            )
        return packets


def _metric(run_id: str, name: str, value: float, t: float) -> MetricRecord:
    return {"run_id": run_id, "metric": name, "value": float(value), "t": t, "tags": {}}
