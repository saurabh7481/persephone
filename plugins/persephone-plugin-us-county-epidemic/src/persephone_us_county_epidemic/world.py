from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any, cast

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict

from persephone_us_county_epidemic.dataset import load_county_graph
from persephone_us_county_epidemic.model import INFECTED, SUSCEPTIBLE


class USCountyWorld(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        if self._initial is None:
            return {"states": (0,)}
        return {key: value.shape for key, value in self._initial.items()}

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        data_path = Path(
            str(
                params.get(
                    "data_path",
                    files("persephone_us_county_epidemic").joinpath("data/county_adjacency2023.txt"),
                )
            )
        )
        graph = load_county_graph(data_path, params)
        states = np.full(len(graph.geoids), SUSCEPTIBLE, dtype=np.int8)
        initially_infected = _initial_infections(params, graph.geoids, seed)
        states[initially_infected] = INFECTED

        self._initial = {
            "states": states,
            "edge_sources": graph.edge_sources,
            "edge_targets": graph.edge_targets,
            "edge_weights": graph.edge_weights,
            "node_geoids": np.asarray([int(geoid) for geoid in graph.geoids], dtype=np.int64),
            "p_infect": np.array([float(params.get("p_infect", 0.3))], dtype=np.float64),
            "p_recover": np.array([float(params.get("p_recover", 0.1))], dtype=np.float64),
            "last_new_infections": np.array([0], dtype=np.int64),
            "last_new_recoveries": np.array([0], dtype=np.int64),
        }
        return {key: value.copy() for key, value in self._initial.items()}

    def reset(self) -> StateDict:
        if self._initial is None:
            raise RuntimeError("World has not been initialized")
        return {key: value.copy() for key, value in self._initial.items()}


def _initial_infections(
    params: dict[str, Any],
    geoids: tuple[str, ...],
    seed: int,
) -> np.ndarray[Any, Any]:
    infected_geoids = params.get("initially_infected_geoids")
    geoid_to_index = {geoid: index for index, geoid in enumerate(geoids)}
    if infected_geoids is not None:
        selected = _string_list(infected_geoids)
        if not selected:
            raise ValueError("initially_infected_geoids must contain at least one county GEOID")
        try:
            return np.asarray([geoid_to_index[geoid] for geoid in selected], dtype=np.int64)
        except KeyError as exc:
            raise ValueError(
                f"Unknown county GEOID in initially_infected_geoids: {exc.args[0]}"
            ) from exc

    count = int(cast(int | float | str, params.get("initially_infected", 1)))
    if count < 1:
        raise ValueError("initially_infected must be at least 1")
    rng = np.random.default_rng(seed)
    sample_size = min(count, len(geoids))
    return np.asarray(rng.choice(len(geoids), size=sample_size, replace=False), dtype=np.int64)


def _string_list(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ValueError("Expected a string or list of county GEOIDs")
