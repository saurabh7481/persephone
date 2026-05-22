from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SPRING_SNOWMELT_IDS = [0, 1, 3, 9]    # Fort Benton, Bismarck, Platte, Minnesota
GULF_HURRICANE_IDS = [20, 23, 24, 26]  # Wabash, Arkansas, Yazoo, Red River


@dataclass(frozen=True)
class FloodNetworkData:
    names: tuple[str, ...]
    states: tuple[str, ...]
    lats: np.ndarray
    lons: np.ndarray
    normal_flow_cms: np.ndarray
    flood_stage_cms: np.ndarray
    river_km: np.ndarray
    upstream_ids: np.ndarray
    downstream_ids: np.ndarray
    travel_time_hours: np.ndarray


def load_flood_network(gauges_path: str | Path, network_path: str | Path) -> FloodNetworkData:
    gauges_path = Path(gauges_path)
    network_path = Path(network_path)

    names: list[str] = []
    states: list[str] = []
    lats: list[float] = []
    lons: list[float] = []
    normal_flow: list[float] = []
    flood_stage: list[float] = []
    river_km: list[float] = []

    with gauges_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            names.append(row["name"])
            states.append(row["state"])
            lats.append(float(row["lat"]))
            lons.append(float(row["lon"]))
            normal_flow.append(float(row["normal_flow_cms"]))
            flood_stage.append(float(row["flood_stage_cms"]))
            river_km.append(float(row["river_km"]))

    upstream: list[int] = []
    downstream: list[int] = []
    travel: list[float] = []

    with network_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            upstream.append(int(row["upstream_id"]))
            downstream.append(int(row["downstream_id"]))
            travel.append(float(row["travel_time_hours"]))

    return FloodNetworkData(
        names=tuple(names),
        states=tuple(states),
        lats=np.array(lats, dtype=np.float64),
        lons=np.array(lons, dtype=np.float64),
        normal_flow_cms=np.array(normal_flow, dtype=np.float64),
        flood_stage_cms=np.array(flood_stage, dtype=np.float64),
        river_km=np.array(river_km, dtype=np.float64),
        upstream_ids=np.array(upstream, dtype=np.int64),
        downstream_ids=np.array(downstream, dtype=np.int64),
        travel_time_hours=np.array(travel, dtype=np.float64),
    )


def injection_station_ids(preset: str, custom: list[int]) -> list[int]:
    if preset == "spring_snowmelt":
        return SPRING_SNOWMELT_IDS
    if preset == "gulf_hurricane":
        return GULF_HURRICANE_IDS
    if preset == "custom":
        return custom
    raise ValueError(f"Unknown event preset: {preset!r}. Choose spring_snowmelt, gulf_hurricane, or custom.")
