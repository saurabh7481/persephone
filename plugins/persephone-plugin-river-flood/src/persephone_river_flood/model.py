from __future__ import annotations

import numpy as np

NORMAL: int = 0
WATCH: int = 1
WARNING: int = 2
FLOOD: int = 3

_WATCH_RATIO = 0.7
_WARNING_RATIO = 0.9
_SECONDS_PER_STEP = 3600.0  # 1-hour steps


def route_step(
    storage_m3: np.ndarray,
    flow_cms: np.ndarray,
    upstream_ids: np.ndarray,
    downstream_ids: np.ndarray,
    edge_weights: np.ndarray,
    precip_input_cms: np.ndarray,
    flood_stage_cms: np.ndarray,
    normal_flow_cms: np.ndarray,
    routing_k: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Linear reservoir routing — one hour step.

    Returns (new_storage_m3, new_flow_cms, new_flood_status).
    edge_weights should be 1/travel_time_hours (faster route = stronger coupling).
    """
    inflow_cms = precip_input_cms.copy()

    # accumulate inflow from upstream neighbours
    for i in range(len(upstream_ids)):
        src = int(upstream_ids[i])
        tgt = int(downstream_ids[i])
        w = float(edge_weights[i])
        inflow_cms[tgt] += flow_cms[src] * w

    # linear reservoir: drain fraction routing_k of storage per step
    outflow_m3 = np.maximum(storage_m3 * routing_k, 0.0)
    outflow_cms = outflow_m3 / _SECONDS_PER_STEP

    new_storage = np.maximum(storage_m3 + (inflow_cms - outflow_cms) * _SECONDS_PER_STEP, 0.0)
    new_flow = outflow_cms

    return new_storage, new_flow, classify_flood_status(new_flow, flood_stage_cms)


def classify_flood_status(flow_cms: np.ndarray, flood_stage_cms: np.ndarray) -> np.ndarray:
    status = np.full(len(flow_cms), NORMAL, dtype=np.int8)
    status[flow_cms >= flood_stage_cms * _WATCH_RATIO] = WATCH
    status[flow_cms >= flood_stage_cms * _WARNING_RATIO] = WARNING
    status[flow_cms >= flood_stage_cms] = FLOOD
    return status


def flood_status_label(code: int) -> str:
    return {NORMAL: "normal", WATCH: "watch", WARNING: "warning", FLOOD: "flood"}.get(
        code, "unknown"
    )


def steady_state_storage(normal_flow_cms: np.ndarray, routing_k: float) -> np.ndarray:
    """Initial storage so each station starts at its normal flow."""
    return normal_flow_cms * _SECONDS_PER_STEP / max(routing_k, 1e-9)
