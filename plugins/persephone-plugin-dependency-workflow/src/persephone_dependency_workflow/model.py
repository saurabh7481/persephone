from __future__ import annotations

from typing import TypedDict

import numpy as np


class ServiceProfile(TypedDict):
    id: str
    label: str
    group: str
    owner: str
    tier: str
    base_risk: float
    base_backlog: float


SERVICES: tuple[ServiceProfile, ...] = (
    {
        "id": "ingest",
        "label": "Ingest gateway",
        "group": "foundation",
        "owner": "Platform intake",
        "tier": "tier_0",
        "base_risk": 0.24,
        "base_backlog": 3.0,
    },
    {
        "id": "rules",
        "label": "Rules engine",
        "group": "decisioning",
        "owner": "Risk automation",
        "tier": "tier_1",
        "base_risk": 0.38,
        "base_backlog": 5.0,
    },
    {
        "id": "pricing",
        "label": "Pricing service",
        "group": "decisioning",
        "owner": "Revenue systems",
        "tier": "tier_1",
        "base_risk": 0.41,
        "base_backlog": 4.0,
    },
    {
        "id": "settlement",
        "label": "Settlement worker",
        "group": "execution",
        "owner": "Finance platform",
        "tier": "tier_1",
        "base_risk": 0.3,
        "base_backlog": 2.0,
    },
    {
        "id": "developer_portal",
        "label": "Developer portal",
        "group": "experience",
        "owner": "Developer experience",
        "tier": "tier_2",
        "base_risk": 0.2,
        "base_backlog": 6.0,
    },
)

EDGES: tuple[tuple[int, int, float], ...] = (
    (0, 1, 0.95),
    (0, 2, 0.82),
    (1, 3, 0.88),
    (2, 3, 0.79),
    (1, 4, 0.54),
    (2, 4, 0.67),
)


def service_ids() -> list[str]:
    return [service["id"] for service in SERVICES]


def base_risk_vector() -> np.ndarray:
    return np.array([service["base_risk"] for service in SERVICES], dtype=np.float64)


def base_backlog_vector() -> np.ndarray:
    return np.array([service["base_backlog"] for service in SERVICES], dtype=np.float64)


def edge_sources_array() -> np.ndarray:
    return np.array([source for source, _, _ in EDGES], dtype=np.int64)


def edge_targets_array() -> np.ndarray:
    return np.array([target for _, target, _ in EDGES], dtype=np.int64)


def edge_weights_array() -> np.ndarray:
    return np.array([weight for _, _, weight in EDGES], dtype=np.float64)


def workflow_state(value: float) -> str:
    if value >= 0.7:
        return "blocked"
    if value >= 0.42:
        return "watch"
    return "healthy"
