from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CountyGraphData:
    geoids: tuple[str, ...]
    names: tuple[str, ...]
    edge_sources: np.ndarray[Any, Any]
    edge_targets: np.ndarray[Any, Any]
    edge_weights: np.ndarray[Any, Any]


def load_county_graph(path: str | Path, params: dict[str, Any]) -> CountyGraphData:
    selected_geoids = _string_set(params.get("county_geoids"))
    geoid_prefixes = _string_list(params.get("geoid_prefixes"))
    county_names: dict[str, str] = {}
    edges: set[tuple[str, str]] = set()

    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        required = {"County Name", "County GEOID", "Neighbor Name", "Neighbor GEOID"}
        if not set(reader.fieldnames or ()).issuperset(required):
            raise ValueError(
                "County adjacency file must contain County/Neighbor name and GEOID columns"
            )

        for row in reader:
            county_geoid = str(row["County GEOID"]).strip()
            neighbor_geoid = str(row["Neighbor GEOID"]).strip()
            if not _selected(
                county_geoid,
                selected_geoids=selected_geoids,
                prefixes=geoid_prefixes,
            ):
                continue
            if not _selected(
                neighbor_geoid,
                selected_geoids=selected_geoids,
                prefixes=geoid_prefixes,
            ):
                continue

            county_names.setdefault(county_geoid, str(row["County Name"]).strip())
            county_names.setdefault(neighbor_geoid, str(row["Neighbor Name"]).strip())
            if county_geoid == neighbor_geoid:
                continue
            edges.add(tuple(sorted((county_geoid, neighbor_geoid))))

    if not county_names:
        raise ValueError("No counties matched the requested GEOID selection")

    ordered_geoids = tuple(sorted(county_names))
    geoid_to_index = {geoid: index for index, geoid in enumerate(ordered_geoids)}
    ordered_names = tuple(county_names[geoid] for geoid in ordered_geoids)
    ordered_edges = sorted(edges)

    return CountyGraphData(
        geoids=ordered_geoids,
        names=ordered_names,
        edge_sources=np.asarray(
            [geoid_to_index[source] for source, _ in ordered_edges],
            dtype=np.int64,
        ),
        edge_targets=np.asarray(
            [geoid_to_index[target] for _, target in ordered_edges],
            dtype=np.int64,
        ),
        edge_weights=np.ones(len(ordered_edges), dtype=np.float64),
    )


def _selected(
    geoid: str,
    *,
    selected_geoids: set[str] | None,
    prefixes: tuple[str, ...] | None,
) -> bool:
    if selected_geoids is not None:
        return geoid in selected_geoids
    if prefixes is not None:
        return any(geoid.startswith(prefix) for prefix in prefixes)
    return True


def _string_list(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        items = tuple(item.strip() for item in value.split(",") if item.strip())
        return items or None
    if isinstance(value, list):
        items = tuple(str(item).strip() for item in value if str(item).strip())
        return items or None
    raise ValueError("Expected a string or list of strings")


def _string_set(value: object) -> set[str] | None:
    items = _string_list(value)
    return set(items) if items is not None else None
