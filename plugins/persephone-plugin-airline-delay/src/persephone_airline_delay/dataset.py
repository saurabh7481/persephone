from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class AirportGraphData:
    iata: tuple[str, ...]
    names: tuple[str, ...]
    lats: np.ndarray
    lons: np.ndarray
    route_counts: np.ndarray
    edge_sources: np.ndarray
    edge_targets: np.ndarray
    edge_weights: np.ndarray
    iata_to_index: dict[str, int]


def load_airport_graph(airports_path: str | Path, routes_path: str | Path) -> AirportGraphData:
    airports_path = Path(airports_path)
    routes_path = Path(routes_path)

    iata_list: list[str] = []
    names: list[str] = []
    lats: list[float] = []
    lons: list[float] = []
    route_counts: list[int] = []

    with airports_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            iata_list.append(row["iata"])
            names.append(row["name"])
            lats.append(float(row["lat"]))
            lons.append(float(row["lon"]))
            route_counts.append(int(row["route_count"]))

    iata_to_index = {iata: i for i, iata in enumerate(iata_list)}

    src_list: list[int] = []
    tgt_list: list[int] = []
    wgt_list: list[float] = []

    with routes_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            src_list.append(int(row["src_id"]))
            tgt_list.append(int(row["dst_id"]))
            wgt_list.append(float(row["weight"]))

    return AirportGraphData(
        iata=tuple(iata_list),
        names=tuple(names),
        lats=np.array(lats, dtype=np.float64),
        lons=np.array(lons, dtype=np.float64),
        route_counts=np.array(route_counts, dtype=np.int64),
        edge_sources=np.array(src_list, dtype=np.int64),
        edge_targets=np.array(tgt_list, dtype=np.int64),
        edge_weights=np.array(wgt_list, dtype=np.float64),
        iata_to_index=iata_to_index,
    )
