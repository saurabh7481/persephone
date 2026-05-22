from __future__ import annotations

from typing import TypedDict

import numpy as np


class SectorProfile(TypedDict):
    id: str
    label: str
    group: str
    mandate: str
    liquidity_bucket: str
    beta: float
    base_risk: float


SECTORS: tuple[SectorProfile, ...] = (
    {
        "id": "technology",
        "label": "Technology",
        "group": "growth",
        "mandate": "Platform and software leaders",
        "liquidity_bucket": "mega_cap",
        "beta": 1.24,
        "base_risk": 0.42,
    },
    {
        "id": "financials",
        "label": "Financials",
        "group": "core",
        "mandate": "Banks, exchanges, and lenders",
        "liquidity_bucket": "large_cap",
        "beta": 0.97,
        "base_risk": 0.35,
    },
    {
        "id": "energy",
        "label": "Energy",
        "group": "cyclical",
        "mandate": "Producers exposed to commodity shocks",
        "liquidity_bucket": "large_cap",
        "beta": 1.11,
        "base_risk": 0.29,
    },
    {
        "id": "industrials",
        "label": "Industrials",
        "group": "cyclical",
        "mandate": "Logistics and capital goods operators",
        "liquidity_bucket": "mid_cap",
        "beta": 0.89,
        "base_risk": 0.32,
    },
)

EDGES: tuple[tuple[int, int, float], ...] = (
    (0, 1, 0.82),
    (0, 2, 0.74),
    (0, 3, 0.58),
    (1, 2, 0.69),
    (1, 3, 0.63),
    (2, 3, 0.57),
)


def sector_ids() -> list[str]:
    return [sector["id"] for sector in SECTORS]


def sector_labels() -> list[str]:
    return [sector["label"] for sector in SECTORS]


def base_risk_vector() -> np.ndarray:
    return np.array([sector["base_risk"] for sector in SECTORS], dtype=np.float64)


def beta_vector() -> np.ndarray:
    return np.array([sector["beta"] for sector in SECTORS], dtype=np.float64)


def edge_sources_array() -> np.ndarray:
    return np.array([source for source, _, _ in EDGES], dtype=np.int64)


def edge_targets_array() -> np.ndarray:
    return np.array([target for _, target, _ in EDGES], dtype=np.int64)


def edge_weights_array() -> np.ndarray:
    return np.array([weight for _, _, weight in EDGES], dtype=np.float64)


def stress_state(value: float) -> str:
    if value >= 0.72:
        return "stressed"
    if value >= 0.46:
        return "watch"
    return "stable"
