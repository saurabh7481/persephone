from __future__ import annotations

import numpy as np

NORMAL: int = 0
MINOR: int = 1
MAJOR: int = 2
DISRUPTED: int = 3

_THRESHOLDS = ((15.0, MINOR), (45.0, MAJOR), (120.0, DISRUPTED))


def delay_step(
    delay_minutes: np.ndarray,
    edge_sources: np.ndarray,
    edge_targets: np.ndarray,
    edge_weights: np.ndarray,
    propagation_factor: float,
    recovery_rate: float,
) -> np.ndarray:
    """One-hour propagation + recovery step. Returns new delay array."""
    num_nodes = len(delay_minutes)
    sum_weights = np.zeros(num_nodes, dtype=np.float64)
    for i in range(len(edge_sources)):
        src = int(edge_sources[i])
        tgt = int(edge_targets[i])
        w = float(edge_weights[i])
        sum_weights[src] += w
        sum_weights[tgt] += w
    sum_weights = np.maximum(sum_weights, 1.0)
    norm_factor = sum_weights ** 0.99

    additions = np.zeros_like(delay_minutes)
    for i in range(len(edge_sources)):
        src = int(edge_sources[i])
        tgt = int(edge_targets[i])
        w = float(edge_weights[i])
        additions[tgt] += (delay_minutes[src] / norm_factor[src]) * w * propagation_factor
        additions[src] += (delay_minutes[tgt] / norm_factor[tgt]) * w * propagation_factor
    new_delay = delay_minutes * (1.0 - recovery_rate) + additions
    return np.maximum(new_delay, 0.0)


def classify_status(delay_minutes: np.ndarray) -> np.ndarray:
    status = np.full(len(delay_minutes), NORMAL, dtype=np.int8)
    for threshold, code in _THRESHOLDS:
        status[delay_minutes >= threshold] = code
    return status


def status_label(code: int) -> str:
    return {NORMAL: "normal", MINOR: "minor", MAJOR: "major", DISRUPTED: "disrupted"}.get(
        code, "unknown"
    )
