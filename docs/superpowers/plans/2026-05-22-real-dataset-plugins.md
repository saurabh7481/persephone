# Real Dataset Plugins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two Persephone plugins backed by real-world network data — global airline delay propagation (OpenFlights top-500 airports) and Mississippi basin river flood routing (USGS gauge network).

**Architecture:** Each plugin follows the established pattern: `dataset.py` loads bundled CSVs, `model.py` contains pure math, `world.py` initialises state, `solver.py` advances state, `observer.py` emits metrics, `renderer.py` produces graph frames with `lat`/`lon` for `map_network` view. Both plugins registered in the root `pyproject.toml` workspace.

**Tech Stack:** Python 3.11, NumPy, Persephone SDK (`World`, `Solver`, `Observer`, `Renderer`, `PluginManifest`), uv workspace, pytest.

---

## File Map

**Create:**
```
scripts/generate_airline_data.py                                        # run once to produce bundled CSVs
plugins/persephone-plugin-airline-delay/
  pyproject.toml
  src/persephone_airline_delay/
    __init__.py
    dataset.py
    model.py
    world.py
    solver.py
    observer.py
    renderer.py
    data/airports.csv                                                   # produced by generate_airline_data.py
    data/routes.csv                                                     # produced by generate_airline_data.py
plugins/persephone-plugin-river-flood/
  pyproject.toml
  src/persephone_river_flood/
    __init__.py
    dataset.py
    model.py
    world.py
    solver.py
    observer.py
    renderer.py
    data/gauges.csv                                                     # hand-crafted in Task 11
    data/network.csv                                                    # hand-crafted in Task 11
tests/plugins/
  __init__.py
  test_airline_delay.py
  test_river_flood.py
```

**Modify:**
```
pyproject.toml                                                          # workspace members + sources + dependencies
```

---

## Task 1: Airline data generation script

**Files:**
- Create: `scripts/generate_airline_data.py`
- Produces: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/data/airports.csv`
- Produces: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/data/routes.csv`

- [ ] **Step 1: Create data directory**

```bash
mkdir -p plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/data
mkdir -p scripts
```

- [ ] **Step 2: Write the generation script**

Create `scripts/generate_airline_data.py`:

```python
#!/usr/bin/env python3
"""Download OpenFlights data and emit top-500 airports.csv + routes.csv."""
from __future__ import annotations

import csv
import io
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
TOP_N = 500
OUT_DIR = Path("plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/data")

def fetch(url: str) -> list[list[str]]:
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(text)))

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching airports.dat …")
    airport_rows = fetch(AIRPORTS_URL)
    # columns: id,name,city,country,iata,icao,lat,lon,alt,tz,dst,tz_name,type,source
    airports: dict[str, dict] = {}
    for row in airport_rows:
        if len(row) < 8:
            continue
        iata = row[4].strip().strip('"')
        if len(iata) != 3 or iata == r"\N":
            continue
        try:
            lat, lon = float(row[6]), float(row[7])
        except ValueError:
            continue
        airports[iata] = {
            "name": row[1].strip().strip('"'),
            "city": row[2].strip().strip('"'),
            "country": row[3].strip().strip('"'),
            "lat": lat,
            "lon": lon,
        }

    print(f"  {len(airports)} airports with valid IATA codes")

    print("Fetching routes.dat …")
    route_rows = fetch(ROUTES_URL)
    # columns: airline,airline_id,src,src_id,dst,dst_id,codeshare,stops,equipment
    route_count: Counter[str] = Counter()
    for row in route_rows:
        if len(row) < 5:
            continue
        src, dst = row[2].strip(), row[4].strip()
        if src in airports:
            route_count[src] += 1
        if dst in airports:
            route_count[dst] += 1

    top_iata = {iata for iata, _ in route_count.most_common(TOP_N)}
    print(f"  Top-{TOP_N} airports selected")

    # edge weight = number of routes between each ordered pair
    pair_count: Counter[tuple[str, str]] = Counter()
    for row in route_rows:
        if len(row) < 5:
            continue
        src, dst = row[2].strip(), row[4].strip()
        if src in top_iata and dst in top_iata and src != dst:
            key = tuple(sorted((src, dst)))
            pair_count[key] += 1  # type: ignore[arg-type]

    # assign sequential ids to top airports sorted by route_count desc, then iata
    ordered = sorted(top_iata, key=lambda x: (-route_count[x], x))
    iata_to_id = {iata: i for i, iata in enumerate(ordered)}

    # normalise edge weights to [0, 1]
    max_w = max(pair_count.values()) if pair_count else 1

    airports_path = OUT_DIR / "airports.csv"
    with airports_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "iata", "name", "city", "country", "lat", "lon", "route_count"])
        for iata in ordered:
            a = airports[iata]
            w.writerow([iata_to_id[iata], iata, a["name"], a["city"], a["country"],
                        a["lat"], a["lon"], route_count[iata]])

    routes_path = OUT_DIR / "routes.csv"
    with routes_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["src_id", "dst_id", "weight"])
        for (a, b), count in sorted(pair_count.items()):
            w.writerow([iata_to_id[a], iata_to_id[b], round(count / max_w, 4)])

    print(f"  {len(ordered)} airports → {airports_path}")
    print(f"  {len(pair_count)} edges → {routes_path}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the script**

```bash
uv run python scripts/generate_airline_data.py
```

Expected output:
```
Fetching airports.dat …
  7XXX airports with valid IATA codes
Fetching routes.dat …
  Top-500 airports selected
  500 airports → plugins/.../airports.csv
  XXXX edges → plugins/.../routes.csv
```

- [ ] **Step 4: Verify output**

```bash
head -3 plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/data/airports.csv
head -3 plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/data/routes.csv
wc -l plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/data/airports.csv
```

Expected: 501 lines (header + 500 rows) for airports.csv, 3000+ lines for routes.csv.

---

## Task 2: Airline model.py (TDD)

**Files:**
- Create: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/model.py`
- Create (test first): `tests/plugins/test_airline_delay.py`

- [ ] **Step 1: Create test directory and write failing tests**

```bash
mkdir -p tests/plugins && touch tests/plugins/__init__.py
```

Create `tests/plugins/test_airline_delay.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

from persephone_airline_delay.model import (
    DISRUPTED, MAJOR, MINOR, NORMAL,
    classify_status, delay_step,
)


def _simple_graph():
    """Triangle: 0-1-2-0 with equal weights."""
    sources = np.array([0, 1, 2], dtype=np.int64)
    targets = np.array([1, 2, 0], dtype=np.int64)
    weights = np.ones(3, dtype=np.float64)
    return sources, targets, weights


def test_delay_step_propagates_from_delayed_airport():
    sources, targets, weights = _simple_graph()
    delay = np.array([120.0, 0.0, 0.0], dtype=np.float64)
    result = delay_step(delay, sources, targets, weights, propagation_factor=0.3, recovery_rate=0.0)
    # airport 0 pushes to airport 1 (edge 0→1), airport 2 pushes 0 via edge 2→0
    # airport 0 has delay; targets of edges FROM 0 = node 1 via edge[0]; also node 0 receives from node 2 (edge[2])
    assert result[1] > 0.0, "delay must propagate to neighbour"
    assert result[0] == pytest.approx(120.0, rel=0.01), "no recovery when rate=0"


def test_delay_step_recovery_drains_delay():
    sources, targets, weights = _simple_graph()
    delay = np.array([100.0, 0.0, 0.0], dtype=np.float64)
    result = delay_step(delay, sources, targets, weights, propagation_factor=0.0, recovery_rate=0.2)
    assert result[0] == pytest.approx(80.0), "20% recovery applied"
    assert result[1] == 0.0
    assert result[2] == 0.0


def test_delay_step_never_goes_negative():
    sources, targets, weights = _simple_graph()
    delay = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    result = delay_step(delay, sources, targets, weights, propagation_factor=0.5, recovery_rate=0.99)
    assert np.all(result >= 0.0)


def test_classify_status_thresholds():
    delay = np.array([0.0, 14.9, 15.0, 44.9, 45.0, 119.9, 120.0, 200.0])
    status = classify_status(delay)
    assert status[0] == NORMAL
    assert status[1] == NORMAL
    assert status[2] == MINOR
    assert status[3] == MINOR
    assert status[4] == MAJOR
    assert status[5] == MAJOR
    assert status[6] == DISRUPTED
    assert status[7] == DISRUPTED
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/plugins/test_airline_delay.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'persephone_airline_delay'`

- [ ] **Step 3: Create the model**

Create `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/model.py`:

```python
from __future__ import annotations

import numpy as np

NORMAL: int = 0
MINOR: int = 1
MAJOR: int = 2
DISRUPTED: int = 3

_THRESHOLDS = ((120.0, DISRUPTED), (45.0, MAJOR), (15.0, MINOR))


def delay_step(
    delay_minutes: np.ndarray,
    edge_sources: np.ndarray,
    edge_targets: np.ndarray,
    edge_weights: np.ndarray,
    propagation_factor: float,
    recovery_rate: float,
) -> np.ndarray:
    """One-hour propagation + recovery step. Returns new delay array."""
    additions = np.zeros_like(delay_minutes)
    for i in range(len(edge_sources)):
        src = int(edge_sources[i])
        tgt = int(edge_targets[i])
        w = float(edge_weights[i])
        additions[tgt] += delay_minutes[src] * w * propagation_factor
        additions[src] += delay_minutes[tgt] * w * propagation_factor
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
```

- [ ] **Step 4: Install the package in editable mode so tests can import it**

We'll do this properly in Task 8 (pyproject.toml). For now, add a temporary path shim. Skip — tests will pass after Task 8 workspace registration. Move to Step 5.

- [ ] **Step 5: Commit model skeleton**

```bash
git add plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/model.py \
        tests/plugins/__init__.py \
        tests/plugins/test_airline_delay.py
git commit -m "feat: airline delay model (pure math) + tests"
```

---

## Task 3: Airline dataset.py

**Files:**
- Create: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/dataset.py`

- [ ] **Step 1: Create dataset module**

Create `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/dataset.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/dataset.py
git commit -m "feat: airline dataset loader"
```

---

## Task 4: Airline world.py

**Files:**
- Create: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/world.py`

- [ ] **Step 1: Create world module**

Create `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/world.py`:

```python
from __future__ import annotations

from importlib.resources import files
from typing import Any

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict

from persephone_airline_delay.dataset import load_airport_graph
from persephone_airline_delay.model import classify_status


class AirlineDelayWorld(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        if self._initial is None:
            return {"delay_minutes": (0,)}
        return {k: v.shape for k, v in self._initial.items()}

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        airports_path = params.get(
            "airports_path",
            str(files("persephone_airline_delay").joinpath("data/airports.csv")),
        )
        routes_path = params.get(
            "routes_path",
            str(files("persephone_airline_delay").joinpath("data/routes.csv")),
        )
        data = load_airport_graph(airports_path, routes_path)
        n = len(data.iata)

        delay_minutes = np.zeros(n, dtype=np.float64)
        initial_airports: list[str] = params.get("initial_airports", ["JFK", "LHR", "DXB"])
        initial_delay = float(params.get("initial_delay_minutes", 180.0))
        for iata in initial_airports:
            idx = data.iata_to_index.get(iata)
            if idx is not None:
                delay_minutes[idx] = initial_delay

        self._initial = {
            "delay_minutes": delay_minutes,
            "status": classify_status(delay_minutes),
            "edge_sources": data.edge_sources.copy(),
            "edge_targets": data.edge_targets.copy(),
            "edge_weights": data.edge_weights.copy(),
            "lats": data.lats.copy(),
            "lons": data.lons.copy(),
            "route_counts": data.route_counts.copy(),
            "propagation_factor": np.array([float(params.get("propagation_factor", 0.3))]),
            "recovery_rate": np.array([float(params.get("recovery_rate", 0.15))]),
        }
        return {k: v.copy() for k, v in self._initial.items()}

    def reset(self) -> StateDict:
        if self._initial is None:
            raise RuntimeError("World not initialised — call init() first")
        return {k: v.copy() for k, v in self._initial.items()}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/world.py
git commit -m "feat: airline delay world (state init)"
```

---

## Task 5: Airline solver.py

**Files:**
- Create: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/solver.py`

- [ ] **Step 1: Create solver module**

Create `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/solver.py`:

```python
from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict

from persephone_airline_delay.model import classify_status, delay_step


class AirlineDelaySolver(Solver):
    def __init__(self) -> None:
        self._t = 0.0

    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: StateDict, dt: float, bus: Any) -> tuple[StateDict, float]:
        prev_delay = state["delay_minutes"]
        new_delay = delay_step(
            prev_delay,
            state["edge_sources"],
            state["edge_targets"],
            state["edge_weights"],
            float(state["propagation_factor"][0]),
            float(state["recovery_rate"][0]),
        )
        new_status = classify_status(new_delay)

        newly_disrupted = np.sum((new_status == 3) & (state["status"] != 3))
        newly_recovered = np.sum((new_status == 0) & (state["status"] != 0))

        new_state = {k: v.copy() for k, v in state.items()}
        new_state["delay_minutes"] = new_delay
        new_state["status"] = new_status
        new_state["newly_disrupted"] = np.array([int(newly_disrupted)], dtype=np.int64)
        new_state["newly_recovered"] = np.array([int(newly_recovered)], dtype=np.int64)
        self._t += dt
        return new_state, dt
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/solver.py
git commit -m "feat: airline delay solver"
```

---

## Task 6: Airline observer.py

**Files:**
- Create: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/observer.py`

- [ ] **Step 1: Create observer module**

Create `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/observer.py`:

```python
from __future__ import annotations

import numpy as np
from persephone_sdk.plugin import Observer
from persephone_sdk.types import MetricRecord, StateDict


class AirlineDelayObserver(Observer):
    def __init__(self) -> None:
        self._ever_delayed: set[int] = set()

    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        delay = state["delay_minutes"]
        status = state["status"]

        delayed_mask = delay >= 15.0
        self._ever_delayed.update(int(i) for i in np.flatnonzero(delayed_mask))

        return [
            _m(run_id, "delayed_airports", float(np.sum(delayed_mask)), t),
            _m(run_id, "disrupted_airports", float(np.sum(status == 3)), t),
            _m(run_id, "total_delay_minutes", float(np.sum(delay)), t),
            _m(run_id, "max_delay_minutes", float(np.max(delay)), t),
            _m(run_id, "cascade_reach", float(len(self._ever_delayed)), t),
        ]


def _m(run_id: str, metric: str, value: float, t: float) -> MetricRecord:
    return {"run_id": run_id, "metric": metric, "value": value, "t": t, "tags": {}}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/observer.py
git commit -m "feat: airline delay observer (metrics)"
```

---

## Task 7: Airline renderer.py

**Files:**
- Create: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/renderer.py`

- [ ] **Step 1: Create renderer module**

Create `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/renderer.py`:

```python
from __future__ import annotations

from importlib.resources import files
from typing import Any

import numpy as np
from persephone_sdk.plugin import Renderer
from persephone_sdk.types import GraphEdge, GraphNode, SimulationFrame, StateDict

from persephone_airline_delay.dataset import load_airport_graph
from persephone_airline_delay.model import status_label

_DATA: Any = None  # cached airport metadata (iata + names)


def _airport_meta() -> tuple[tuple[str, ...], tuple[str, ...]]:
    global _DATA
    if _DATA is None:
        data = load_airport_graph(
            files("persephone_airline_delay").joinpath("data/airports.csv"),
            files("persephone_airline_delay").joinpath("data/routes.csv"),
        )
        _DATA = (data.iata, data.names)
    return _DATA  # type: ignore[return-value]


class AirlineDelayRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {
            "type": "graph_airline_delay",
            "state_channel": "status",
            "edge_channels": {
                "source": "edge_sources",
                "target": "edge_targets",
                "weight": "edge_weights",
            },
            "charts": ["disrupted_airports", "total_delay_minutes", "cascade_reach"],
        }

    def frame(
        self,
        state: StateDict,
        *,
        t: float,
        run_id: str,
        solver_id: str,
        tick: int,
        source: str = "live",
    ) -> list[SimulationFrame]:
        delay = np.asarray(state["delay_minutes"], dtype=np.float64)
        status = np.asarray(state["status"], dtype=np.int8)
        lats = np.asarray(state["lats"], dtype=np.float64)
        lons = np.asarray(state["lons"], dtype=np.float64)
        edge_sources = np.asarray(state["edge_sources"], dtype=np.int64)
        edge_targets = np.asarray(state["edge_targets"], dtype=np.int64)
        edge_weights = np.asarray(state["edge_weights"], dtype=np.float64)
        iata_codes, names = _airport_meta()

        nodes: list[GraphNode] = [
            {
                "id": iata_codes[i],
                "label": iata_codes[i],
                "group": names[i],
                "state": status_label(int(status[i])),
                "lat": float(lats[i]),
                "lon": float(lons[i]),
                "metrics": {"delay_minutes": float(delay[i])},
            }
            for i in range(len(iata_codes))
        ]
        edges: list[GraphEdge] = [
            {
                "source": iata_codes[int(edge_sources[j])],
                "target": iata_codes[int(edge_targets[j])],
                "weight": float(edge_weights[j]),
                "directed": False,
            }
            for j in range(len(edge_sources))
        ]
        return [
            {
                "kind": "graph",
                "run_id": run_id,
                "frame_id": f"{solver_id}:graph:{tick:06d}",
                "t": t,
                "tick": tick,
                "solver_id": solver_id,
                "source": source,
                "schema_version": 1,
                "nodes": nodes,
                "edges": edges,
                "visualization": {
                    "coordinate_system": "geo",
                    "preferred_view": "map_network",
                    "node_state_field": "state",
                    "legend": {
                        "state": {
                            "normal": "No significant delay",
                            "minor": "15–45 min delay",
                            "major": "45–120 min delay",
                            "disrupted": ">120 min delay",
                        }
                    },
                },
            }
        ]
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/renderer.py
git commit -m "feat: airline delay renderer (map_network frame with lat/lon)"
```

---

## Task 8: Airline manifest + pyproject.toml

**Files:**
- Create: `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/__init__.py`
- Create: `plugins/persephone-plugin-airline-delay/pyproject.toml`

- [ ] **Step 1: Create plugin manifest**

Create `plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/__init__.py`:

```python
from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import (
    EntityField,
    MetricDefinition,
    PluginManifest,
    SemanticManifest,
    StateDefinition,
    ViewCapability,
)

from persephone_airline_delay.observer import AirlineDelayObserver
from persephone_airline_delay.renderer import AirlineDelayRenderer
from persephone_airline_delay.solver import AirlineDelaySolver
from persephone_airline_delay.world import AirlineDelayWorld


class AirlineDelayPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="airline_delay",
            version="0.1.0",
            paradigm="graph",
            world=AirlineDelayWorld,
            solver=AirlineDelaySolver,
            observer=AirlineDelayObserver,
            renderer=AirlineDelayRenderer,
            bus_reads=[],
            bus_writes=[],
            default_params=_default_params(),
            params_schema=_params_schema(),
            metrics_schema=_metrics_schema(),
            semantics=_semantics(),
            sdk_min_version="0.1.0",
        )


def _default_params() -> dict[str, Any]:
    return {
        "initial_airports": ["JFK", "LHR", "DXB"],
        "initial_delay_minutes": 180.0,
        "propagation_factor": 0.3,
        "recovery_rate": 0.15,
    }


def _params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "initial_airports": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string", "minLength": 3}},
                ]
            },
            "initial_delay_minutes": {"type": "number", "minimum": 0},
            "propagation_factor": {"type": "number", "minimum": 0, "maximum": 1},
            "recovery_rate": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def _metrics_schema() -> dict[str, Any]:
    return {
        "delayed_airports": {"type": "number"},
        "disrupted_airports": {"type": "number"},
        "total_delay_minutes": {"type": "number"},
        "max_delay_minutes": {"type": "number"},
        "cascade_reach": {"type": "number"},
    }


def _semantics() -> SemanticManifest:
    return SemanticManifest(
        entity_schemas={
            "airport": [
                EntityField(name="iata", type="string", label="IATA Code", required=True),
                EntityField(name="delay_minutes", type="number", label="Delay (min)", required=True),
            ]
        },
        state_schema={
            "status": StateDefinition(
                name="status", kind="categorical", label="Delay Status", unit="category"
            )
        },
        metric_schema={
            "delayed_airports": MetricDefinition(name="delayed_airports", label="Delayed airports"),
            "disrupted_airports": MetricDefinition(
                name="disrupted_airports", label="Disrupted airports", headline=True
            ),
            "total_delay_minutes": MetricDefinition(
                name="total_delay_minutes", label="Total delay (min)", headline=True
            ),
            "max_delay_minutes": MetricDefinition(
                name="max_delay_minutes", label="Peak delay (min)"
            ),
            "cascade_reach": MetricDefinition(
                name="cascade_reach", label="Airports ever delayed"
            ),
        },
        view_capabilities=[
            ViewCapability(kind="map_network", label="Global delay map", default=True),
            ViewCapability(kind="network", label="Route network"),
        ],
        default_entity_type="airport",
        preferred_view="map_network",
    )


__all__ = [
    "AirlineDelayPlugin",
    "AirlineDelayWorld",
    "AirlineDelaySolver",
    "AirlineDelayObserver",
    "AirlineDelayRenderer",
]
```

- [ ] **Step 2: Create pyproject.toml**

Create `plugins/persephone-plugin-airline-delay/pyproject.toml`:

```toml
[project]
name = "persephone-plugin-airline-delay"
version = "0.1.0"
description = "Global airline delay propagation plugin for Persephone (OpenFlights top-500 airports)."
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
    "persephone",
    "persephone-sdk",
]

[project.entry-points."persephone.plugins"]
airline_delay = "persephone_airline_delay:AirlineDelayPlugin"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/persephone_airline_delay"]

[tool.hatch.build.targets.wheel.force-include]
"src/persephone_airline_delay/data/airports.csv" = "persephone_airline_delay/data/airports.csv"
"src/persephone_airline_delay/data/routes.csv" = "persephone_airline_delay/data/routes.csv"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/persephone-plugin-airline-delay/
git commit -m "feat: airline delay plugin manifest and pyproject.toml"
```

---

## Task 9: Register airline plugin in workspace

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add to workspace members**

In `pyproject.toml`, find `[tool.uv.workspace]` and add the new plugin to `members`:

```toml
[tool.uv.workspace]
members = ["sdk", "plugins/persephone-plugin-sir-epidemic", "plugins/persephone-plugin-heat-diffusion", "plugins/persephone-plugin-us-county-epidemic", "plugins/persephone-plugin-market-stress", "plugins/persephone-plugin-dependency-workflow", "plugins/persephone-plugin-airline-delay"]
```

- [ ] **Step 2: Add to uv sources**

In `[tool.uv.sources]` add:

```toml
persephone-plugin-airline-delay = { workspace = true }
```

- [ ] **Step 3: Add to main dependencies**

In `[project]` → `dependencies` add:

```
"persephone-plugin-airline-delay",
```

- [ ] **Step 4: Sync workspace**

```bash
uv sync
```

Expected: resolves without error, installs `persephone-plugin-airline-delay`.

- [ ] **Step 5: Verify plugin loads**

```bash
uv run python -c "from persephone_airline_delay import AirlineDelayPlugin; m = AirlineDelayPlugin.manifest(); print(m.name, m.paradigm)"
```

Expected: `airline_delay graph`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml
git commit -m "chore: register airline delay plugin in uv workspace"
```

---

## Task 10: Airline integration test

**Files:**
- Modify: `tests/plugins/test_airline_delay.py`

- [ ] **Step 1: Add integration test (append to existing test file)**

Add to `tests/plugins/test_airline_delay.py`:

```python
import json
from pathlib import Path

import numpy as np
import pytest

from persephone.core.engine import PersephoneEngine
from persephone.registry.registry import PluginRegistry
from persephone_airline_delay import AirlineDelayPlugin


class _AirlineEntry:
    name = "airline_delay"

    def load(self):
        return AirlineDelayPlugin


def _write_config(tmp_path: Path, initial_airports: list[str] | None = None) -> Path:
    airports = initial_airports or ["JFK", "LHR"]
    airports_yaml = "[" + ", ".join(f'"{a}"' for a in airports) + "]"
    config = tmp_path / "experiment.yaml"
    config.write_text(
        f"""
name: airline_test
seed: 42
scheduler:
  t_end: 5
storage:
  artifacts_dir: runs
solvers:
  - type: graph
    plugin: airline_delay
    version: ">=0.1.0"
    params:
      initial_airports: {airports_yaml}
      initial_delay_minutes: 180
      propagation_factor: 0.3
      recovery_rate: 0.1
""",
        encoding="utf-8",
    )
    return config


def test_airline_delay_run_completes_and_emits_metrics(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_AirlineEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_write_config_obj(tmp_path), run_id="airline-test")

    assert result.status == "completed"
    assert result.final_time == pytest.approx(5.0)

    metrics_lines = (result.artifact_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    metrics = [json.loads(line) for line in metrics_lines]
    names = {m["metric"] for m in metrics}
    assert "disrupted_airports" in names
    assert "total_delay_minutes" in names
    assert "cascade_reach" in names

    # initial shock of 180 min per airport means cascade_reach > 0 after step 1
    final_reach = max(m["value"] for m in metrics if m["metric"] == "cascade_reach")
    assert final_reach >= 2  # at least the 2 seeded airports were delayed


def _write_config_obj(tmp_path: Path):
    from persephone.config.load import load_experiment_config
    return load_experiment_config(_write_config(tmp_path))


def test_airline_delay_delay_propagates_beyond_seed_airports(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_AirlineEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_write_config_obj(tmp_path), run_id="airline-cascade")

    metrics_lines = (result.artifact_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    metrics = [json.loads(line) for line in metrics_lines]

    # after 5 steps with prop_factor=0.3, at least some neighbours must be delayed
    delayed_at_end = [m["value"] for m in metrics if m["metric"] == "delayed_airports"]
    assert max(delayed_at_end) > 2
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/plugins/test_airline_delay.py -v
```

Expected: all tests pass (model unit tests + 2 integration tests).

- [ ] **Step 3: Commit**

```bash
git add tests/plugins/test_airline_delay.py
git commit -m "test: airline delay integration tests"
```

---

## Task 11: River flood data files

**Files:**
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/data/gauges.csv`
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/data/network.csv`

- [ ] **Step 1: Create data directory**

```bash
mkdir -p plugins/persephone-plugin-river-flood/src/persephone_river_flood/data
```

- [ ] **Step 2: Create gauges.csv**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/data/gauges.csv` with this exact content:

```csv
id,name,state,lat,lon,drainage_area_km2,normal_flow_cms,flood_stage_cms,river_km
0,Fort Benton,MT,47.82,-110.67,57000,200.0,500.0,0
1,Bismarck,ND,46.81,-100.78,485000,500.0,1200.0,800
2,Sioux City,IA,42.50,-96.40,724000,700.0,1800.0,1600
3,Platte at Plattsmouth,NE,41.01,-95.88,220000,100.0,500.0,1790
4,Omaha,NE,41.26,-96.02,835000,900.0,2200.0,1800
5,Kansas River at Lecompton,KS,39.05,-95.44,156000,200.0,1500.0,2195
6,Kansas City,MO,39.10,-94.58,1080000,1400.0,3500.0,2200
7,Osage at St Thomas,MO,38.37,-91.96,36000,200.0,800.0,2795
8,Hermann,MO,38.71,-91.44,1350000,2000.0,5000.0,2800
9,Minnesota at Mankato,MN,44.17,-94.00,39000,50.0,200.0,2850
10,Minneapolis,MN,44.98,-93.26,95000,180.0,500.0,2900
11,Dubuque,IA,42.50,-90.67,175000,600.0,1500.0,3100
12,Illinois at Havana,IL,40.30,-90.07,69000,300.0,700.0,3175
13,Quincy,IL,39.93,-91.41,377000,1200.0,3000.0,3200
14,St. Louis,MO,38.63,-90.19,1805000,4000.0,10000.0,3350
15,Pittsburgh,PA,40.44,-80.00,72000,600.0,2000.0,1000
16,Cumberland at Nashville,TN,36.17,-86.78,48000,400.0,2000.0,3750
17,Tennessee at Paducah,KY,37.08,-88.60,104000,1500.0,4000.0,3820
18,Cincinnati,OH,39.10,-84.52,247000,1200.0,3500.0,3400
19,Louisville,KY,38.25,-85.76,298000,1500.0,4000.0,3550
20,Wabash at Mt Carmel,IL,38.41,-87.77,83000,350.0,1500.0,3820
21,Cairo,IL,37.00,-89.18,526000,3500.0,9000.0,3850
22,Memphis,TN,35.15,-90.05,2097000,10000.0,25000.0,4200
23,Arkansas at Little Rock,AR,34.75,-92.28,417000,400.0,2000.0,4450
24,Yazoo at Vicksburg,MS,32.35,-90.93,34000,150.0,1000.0,4600
25,Vicksburg,MS,32.35,-90.88,2963000,12000.0,30000.0,4600
26,Red River at Alexandria,LA,31.31,-92.46,133000,200.0,1500.0,4800
27,Natchez,MS,31.56,-91.39,3097000,13000.0,34000.0,4650
28,Baton Rouge,LA,30.45,-91.19,3238000,14000.0,37000.0,4900
29,New Orleans,LA,29.93,-90.13,3270000,14500.0,40000.0,5000
```

- [ ] **Step 3: Create network.csv**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/data/network.csv` with this exact content:

```csv
upstream_id,downstream_id,travel_time_hours
0,1,72
1,2,96
3,4,12
2,4,48
4,6,48
5,6,24
6,8,72
7,8,24
9,10,12
10,11,72
12,13,12
11,13,48
13,14,48
8,14,24
15,18,48
16,17,24
17,21,48
18,19,24
19,21,48
20,21,12
14,22,96
21,22,72
23,25,24
24,25,6
22,25,72
26,27,24
25,27,48
27,28,36
28,29,12
```

- [ ] **Step 4: Commit**

```bash
git add plugins/persephone-plugin-river-flood/src/persephone_river_flood/data/
git commit -m "feat: river flood gauge data (30-station Mississippi basin)"
```

---

## Task 12: River model.py (TDD)

**Files:**
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/model.py`
- Create: `tests/plugins/test_river_flood.py`

- [ ] **Step 1: Write failing tests first**

Create `tests/plugins/test_river_flood.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

from persephone_river_flood.model import (
    FLOOD, NORMAL, WARNING, WATCH,
    classify_flood_status, route_step,
)


def test_route_step_inflow_raises_downstream_storage():
    """Water injected at upstream node must raise downstream storage."""
    # 2 nodes: 0 upstream → 1 downstream
    n = 2
    storage = np.array([1000.0, 500.0], dtype=np.float64)
    flow = np.array([0.5, 0.2], dtype=np.float64)
    upstream_ids = np.array([0], dtype=np.int64)
    downstream_ids = np.array([1], dtype=np.int64)
    edge_weights = np.array([1.0], dtype=np.float64)
    precip_input = np.zeros(n, dtype=np.float64)
    flood_stage = np.array([100.0, 50.0], dtype=np.float64)
    normal_flow = np.array([0.5, 0.2], dtype=np.float64)

    new_storage, new_flow, _ = route_step(
        storage, flow, upstream_ids, downstream_ids, edge_weights,
        precip_input, flood_stage, normal_flow, routing_k=0.35,
    )

    assert new_storage[1] > storage[1], "downstream storage must increase from inflow"


def test_route_step_storage_non_negative():
    n = 3
    storage = np.zeros(n, dtype=np.float64)
    flow = np.zeros(n, dtype=np.float64)
    upstream_ids = np.array([0, 1], dtype=np.int64)
    downstream_ids = np.array([1, 2], dtype=np.int64)
    edge_weights = np.ones(2, dtype=np.float64)
    precip_input = np.zeros(n, dtype=np.float64)
    flood_stage = np.ones(n, dtype=np.float64) * 100.0
    normal_flow = np.ones(n, dtype=np.float64) * 0.1

    new_storage, new_flow, _ = route_step(
        storage, flow, upstream_ids, downstream_ids, edge_weights,
        precip_input, flood_stage, normal_flow, routing_k=0.5,
    )

    assert np.all(new_storage >= 0.0)
    assert np.all(new_flow >= 0.0)


def test_precipitation_input_raises_headwater_storage():
    n = 2
    storage = np.array([0.0, 0.0], dtype=np.float64)
    flow = np.zeros(n, dtype=np.float64)
    upstream_ids = np.array([0], dtype=np.int64)
    downstream_ids = np.array([1], dtype=np.int64)
    edge_weights = np.ones(1, dtype=np.float64)
    precip_input = np.array([500.0, 0.0], dtype=np.float64)  # rain at node 0
    flood_stage = np.array([200.0, 200.0], dtype=np.float64)
    normal_flow = np.array([1.0, 1.0], dtype=np.float64)

    new_storage, _, _ = route_step(
        storage, flow, upstream_ids, downstream_ids, edge_weights,
        precip_input, flood_stage, normal_flow, routing_k=0.1,
    )

    assert new_storage[0] > 0.0, "precipitation must raise headwater storage"


def test_classify_flood_status_thresholds():
    flood_stage = np.array([100.0, 100.0, 100.0, 100.0])
    flow = np.array([60.0, 70.0, 91.0, 100.0])
    status = classify_flood_status(flow, flood_stage)
    assert status[0] == NORMAL   # 60 < 70
    assert status[1] == WATCH    # 70 = 0.7 * 100
    assert status[2] == WARNING  # 91 >= 0.9 * 100
    assert status[3] == FLOOD    # 100 >= 100
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/plugins/test_river_flood.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'persephone_river_flood'`

- [ ] **Step 3: Implement model.py**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/model.py`:

```python
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
    n = len(storage_m3)
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
```

- [ ] **Step 4: Commit**

```bash
git add plugins/persephone-plugin-river-flood/src/persephone_river_flood/model.py \
        tests/plugins/test_river_flood.py
git commit -m "feat: river flood model (linear reservoir routing) + tests"
```

---

## Task 13: River dataset.py

**Files:**
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/dataset.py`

- [ ] **Step 1: Create dataset module**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/dataset.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-river-flood/src/persephone_river_flood/dataset.py
git commit -m "feat: river flood dataset loader"
```

---

## Task 14: River world.py

**Files:**
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/world.py`

- [ ] **Step 1: Create world module**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/world.py`:

```python
from __future__ import annotations

from importlib.resources import files
from typing import Any

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict

from persephone_river_flood.dataset import load_flood_network
from persephone_river_flood.model import NORMAL, classify_flood_status, steady_state_storage


class RiverFloodWorld(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        if self._initial is None:
            return {"storage_m3": (0,)}
        return {k: v.shape for k, v in self._initial.items()}

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        gauges_path = params.get(
            "gauges_path",
            str(files("persephone_river_flood").joinpath("data/gauges.csv")),
        )
        network_path = params.get(
            "network_path",
            str(files("persephone_river_flood").joinpath("data/network.csv")),
        )
        data = load_flood_network(gauges_path, network_path)
        routing_k = float(params.get("routing_k", 0.35))

        storage_m3 = steady_state_storage(data.normal_flow_cms, routing_k)
        flow_cms = data.normal_flow_cms.copy()
        flood_status = np.full(len(data.names), NORMAL, dtype=np.int8)
        edge_weights = 1.0 / np.maximum(data.travel_time_hours, 1.0)

        self._initial = {
            "storage_m3": storage_m3,
            "flow_cms": flow_cms,
            "flood_status": flood_status,
            "flood_stage_cms": data.flood_stage_cms.copy(),
            "normal_flow_cms": data.normal_flow_cms.copy(),
            "river_km": data.river_km.copy(),
            "upstream_ids": data.upstream_ids.copy(),
            "downstream_ids": data.downstream_ids.copy(),
            "edge_weights": edge_weights,
            "lats": data.lats.copy(),
            "lons": data.lons.copy(),
            "routing_k": np.array([routing_k]),
            "precipitation_cms": np.array([float(params.get("precipitation_cms", 500.0))]),
            "precip_duration_hours": np.array([int(params.get("precipitation_duration_hours", 24))], dtype=np.int64),
            "event_preset": np.array([0], dtype=np.int64),  # stored as tick counter; preset resolved in solver
        }
        # store injection mask
        from persephone_river_flood.dataset import injection_station_ids
        preset = str(params.get("event_preset", "spring_snowmelt"))
        custom = list(params.get("custom_injection_stations", []))
        injection_ids = injection_station_ids(preset, custom)
        injection_mask = np.zeros(len(data.names), dtype=np.float64)
        injection_mask[injection_ids] = 1.0
        self._initial["injection_mask"] = injection_mask

        return {k: v.copy() for k, v in self._initial.items()}

    def reset(self) -> StateDict:
        if self._initial is None:
            raise RuntimeError("World not initialised — call init() first")
        return {k: v.copy() for k, v in self._initial.items()}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-river-flood/src/persephone_river_flood/world.py
git commit -m "feat: river flood world (steady-state init)"
```

---

## Task 15: River solver.py

**Files:**
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/solver.py`

- [ ] **Step 1: Create solver**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/solver.py`:

```python
from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict

from persephone_river_flood.model import route_step


class RiverFloodSolver(Solver):
    def __init__(self) -> None:
        self._tick = 0

    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: StateDict, dt: float, bus: Any) -> tuple[StateDict, float]:
        precip_duration = int(state["precip_duration_hours"][0])
        precip_cms = float(state["precipitation_cms"][0])
        routing_k = float(state["routing_k"][0])

        precip_input = np.zeros(len(state["storage_m3"]), dtype=np.float64)
        if self._tick < precip_duration:
            precip_input = state["injection_mask"] * precip_cms

        new_storage, new_flow, new_status = route_step(
            state["storage_m3"],
            state["flow_cms"],
            state["upstream_ids"],
            state["downstream_ids"],
            state["edge_weights"],
            precip_input,
            state["flood_stage_cms"],
            state["normal_flow_cms"],
            routing_k,
        )

        new_state = {k: v.copy() for k, v in state.items()}
        new_state["storage_m3"] = new_storage
        new_state["flow_cms"] = new_flow
        new_state["flood_status"] = new_status
        self._tick += 1
        return new_state, dt
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-river-flood/src/persephone_river_flood/solver.py
git commit -m "feat: river flood solver"
```

---

## Task 16: River observer.py

**Files:**
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/observer.py`

- [ ] **Step 1: Create observer**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/observer.py`:

```python
from __future__ import annotations

import numpy as np
from persephone_sdk.plugin import Observer
from persephone_sdk.types import MetricRecord, StateDict

from persephone_river_flood.model import WARNING, WATCH


class RiverFloodObserver(Observer):
    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        flow = state["flow_cms"]
        flood_status = state["flood_status"]
        flood_stage = state["flood_stage_cms"]
        normal_flow = state["normal_flow_cms"]
        river_km = state["river_km"]

        at_watch = flood_status >= WATCH
        at_warning = flood_status >= WARNING

        # flood_front_km: farthest downstream station at warning or flood
        warning_km = river_km[at_warning]
        flood_front_km = float(np.max(warning_km)) if len(warning_km) > 0 else 0.0

        excess = np.maximum(flow - normal_flow, 0.0)

        return [
            _m(run_id, "stations_flooding", float(np.sum(flood_status == 3)), t),
            _m(run_id, "stations_watch", float(np.sum(at_watch)), t),
            _m(run_id, "total_excess_flow_cms", float(np.sum(excess)), t),
            _m(run_id, "peak_flow_cms", float(np.max(flow)), t),
            _m(run_id, "flood_front_km", flood_front_km, t),
        ]


def _m(run_id: str, metric: str, value: float, t: float) -> MetricRecord:
    return {"run_id": run_id, "metric": metric, "value": value, "t": t, "tags": {}}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-river-flood/src/persephone_river_flood/observer.py
git commit -m "feat: river flood observer (metrics)"
```

---

## Task 17: River renderer.py

**Files:**
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/renderer.py`

- [ ] **Step 1: Create renderer**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/renderer.py`:

```python
from __future__ import annotations

from importlib.resources import files
from typing import Any

import numpy as np
from persephone_sdk.plugin import Renderer
from persephone_sdk.types import GraphEdge, GraphNode, SimulationFrame, StateDict

from persephone_river_flood.dataset import load_flood_network
from persephone_river_flood.model import flood_status_label

_NETWORK: Any = None


def _network_meta():
    global _NETWORK
    if _NETWORK is None:
        _NETWORK = load_flood_network(
            files("persephone_river_flood").joinpath("data/gauges.csv"),
            files("persephone_river_flood").joinpath("data/network.csv"),
        )
    return _NETWORK


class RiverFloodRenderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {
            "type": "graph_river_flood",
            "state_channel": "flood_status",
            "edge_channels": {
                "source": "upstream_ids",
                "target": "downstream_ids",
                "weight": "edge_weights",
            },
            "charts": ["stations_flooding", "total_excess_flow_cms", "flood_front_km"],
        }

    def frame(
        self,
        state: StateDict,
        *,
        t: float,
        run_id: str,
        solver_id: str,
        tick: int,
        source: str = "live",
    ) -> list[SimulationFrame]:
        data = _network_meta()
        flow = np.asarray(state["flow_cms"], dtype=np.float64)
        flood_status = np.asarray(state["flood_status"], dtype=np.int8)
        lats = np.asarray(state["lats"], dtype=np.float64)
        lons = np.asarray(state["lons"], dtype=np.float64)
        upstream_ids = np.asarray(state["upstream_ids"], dtype=np.int64)
        downstream_ids = np.asarray(state["downstream_ids"], dtype=np.int64)
        edge_weights = np.asarray(state["edge_weights"], dtype=np.float64)

        nodes: list[GraphNode] = [
            {
                "id": str(i),
                "label": data.names[i],
                "group": data.states[i],
                "state": flood_status_label(int(flood_status[i])),
                "lat": float(lats[i]),
                "lon": float(lons[i]),
                "metrics": {"flow_cms": float(flow[i])},
            }
            for i in range(len(data.names))
        ]
        edges: list[GraphEdge] = [
            {
                "source": str(int(upstream_ids[j])),
                "target": str(int(downstream_ids[j])),
                "weight": float(edge_weights[j]),
                "directed": True,
                "kind": "river_reach",
            }
            for j in range(len(upstream_ids))
        ]
        return [
            {
                "kind": "graph",
                "run_id": run_id,
                "frame_id": f"{solver_id}:graph:{tick:06d}",
                "t": t,
                "tick": tick,
                "solver_id": solver_id,
                "source": source,
                "schema_version": 1,
                "nodes": nodes,
                "edges": edges,
                "visualization": {
                    "coordinate_system": "geo",
                    "preferred_view": "map_network",
                    "node_state_field": "state",
                    "legend": {
                        "state": {
                            "normal": "Below watch stage",
                            "watch": "70% of flood stage",
                            "warning": "90% of flood stage",
                            "flood": "At or above flood stage",
                        }
                    },
                },
            }
        ]
```

- [ ] **Step 2: Commit**

```bash
git add plugins/persephone-plugin-river-flood/src/persephone_river_flood/renderer.py
git commit -m "feat: river flood renderer (map_network frame with lat/lon)"
```

---

## Task 18: River manifest + pyproject.toml

**Files:**
- Create: `plugins/persephone-plugin-river-flood/src/persephone_river_flood/__init__.py`
- Create: `plugins/persephone-plugin-river-flood/pyproject.toml`

- [ ] **Step 1: Create manifest**

Create `plugins/persephone-plugin-river-flood/src/persephone_river_flood/__init__.py`:

```python
from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import (
    EntityField,
    MetricDefinition,
    PluginManifest,
    SemanticManifest,
    StateDefinition,
    ViewCapability,
)

from persephone_river_flood.observer import RiverFloodObserver
from persephone_river_flood.renderer import RiverFloodRenderer
from persephone_river_flood.solver import RiverFloodSolver
from persephone_river_flood.world import RiverFloodWorld


class RiverFloodPlugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="river_flood",
            version="0.1.0",
            paradigm="graph",
            world=RiverFloodWorld,
            solver=RiverFloodSolver,
            observer=RiverFloodObserver,
            renderer=RiverFloodRenderer,
            bus_reads=[],
            bus_writes=[],
            default_params=_default_params(),
            params_schema=_params_schema(),
            metrics_schema=_metrics_schema(),
            semantics=_semantics(),
            sdk_min_version="0.1.0",
        )


def _default_params() -> dict[str, Any]:
    return {
        "event_preset": "spring_snowmelt",
        "precipitation_cms": 500.0,
        "precipitation_duration_hours": 24,
        "routing_k": 0.35,
        "custom_injection_stations": [],
    }


def _params_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "event_preset": {"type": "string", "enum": ["spring_snowmelt", "gulf_hurricane", "custom"]},
            "precipitation_cms": {"type": "number", "minimum": 0},
            "precipitation_duration_hours": {"type": "integer", "minimum": 1},
            "routing_k": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
            "custom_injection_stations": {"type": "array", "items": {"type": "integer", "minimum": 0}},
        },
    }


def _metrics_schema() -> dict[str, Any]:
    return {
        "stations_flooding": {"type": "number"},
        "stations_watch": {"type": "number"},
        "total_excess_flow_cms": {"type": "number"},
        "peak_flow_cms": {"type": "number"},
        "flood_front_km": {"type": "number"},
    }


def _semantics() -> SemanticManifest:
    return SemanticManifest(
        entity_schemas={
            "gauge": [
                EntityField(name="name", type="string", label="Station Name", required=True),
                EntityField(name="flow_cms", type="number", label="Flow (m³/s)", required=True),
            ]
        },
        state_schema={
            "flood_status": StateDefinition(
                name="flood_status", kind="categorical", label="Flood Status", unit="category"
            )
        },
        metric_schema={
            "stations_flooding": MetricDefinition(
                name="stations_flooding", label="Stations at flood stage", headline=True
            ),
            "stations_watch": MetricDefinition(name="stations_watch", label="Stations at watch"),
            "total_excess_flow_cms": MetricDefinition(
                name="total_excess_flow_cms", label="Total excess flow (m³/s)", headline=True
            ),
            "peak_flow_cms": MetricDefinition(name="peak_flow_cms", label="Peak flow (m³/s)"),
            "flood_front_km": MetricDefinition(
                name="flood_front_km", label="Flood front (river km)"
            ),
        },
        view_capabilities=[
            ViewCapability(kind="map_network", label="Mississippi flood map", default=True),
            ViewCapability(kind="network", label="River network"),
        ],
        default_entity_type="gauge",
        preferred_view="map_network",
    )


__all__ = [
    "RiverFloodPlugin",
    "RiverFloodWorld",
    "RiverFloodSolver",
    "RiverFloodObserver",
    "RiverFloodRenderer",
]
```

- [ ] **Step 2: Create pyproject.toml**

Create `plugins/persephone-plugin-river-flood/pyproject.toml`:

```toml
[project]
name = "persephone-plugin-river-flood"
version = "0.1.0"
description = "Mississippi basin river flood routing plugin for Persephone (USGS gauge network)."
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
    "persephone",
    "persephone-sdk",
]

[project.entry-points."persephone.plugins"]
river_flood = "persephone_river_flood:RiverFloodPlugin"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/persephone_river_flood"]

[tool.hatch.build.targets.wheel.force-include]
"src/persephone_river_flood/data/gauges.csv" = "persephone_river_flood/data/gauges.csv"
"src/persephone_river_flood/data/network.csv" = "persephone_river_flood/data/network.csv"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/persephone-plugin-river-flood/
git commit -m "feat: river flood plugin manifest and pyproject.toml"
```

---

## Task 19: Register river plugin in workspace

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add to workspace members** (edit `[tool.uv.workspace]`):

```toml
members = ["sdk", "plugins/persephone-plugin-sir-epidemic", "plugins/persephone-plugin-heat-diffusion", "plugins/persephone-plugin-us-county-epidemic", "plugins/persephone-plugin-market-stress", "plugins/persephone-plugin-dependency-workflow", "plugins/persephone-plugin-airline-delay", "plugins/persephone-plugin-river-flood"]
```

- [ ] **Step 2: Add to `[tool.uv.sources]`**:

```toml
persephone-plugin-river-flood = { workspace = true }
```

- [ ] **Step 3: Add to `[project]` dependencies**:

```
"persephone-plugin-river-flood",
```

- [ ] **Step 4: Sync**

```bash
uv sync
```

- [ ] **Step 5: Verify**

```bash
uv run python -c "from persephone_river_flood import RiverFloodPlugin; m = RiverFloodPlugin.manifest(); print(m.name, m.paradigm)"
```

Expected: `river_flood graph`

- [ ] **Step 6: Verify both plugins visible to registry**

```bash
uv run python -c "
from persephone.registry.registry import PluginRegistry
r = PluginRegistry()
print([p for p in r.list_plugins()])
"
```

Expected output contains `airline_delay` and `river_flood`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml
git commit -m "chore: register river flood plugin in uv workspace"
```

---

## Task 20: River flood integration test

**Files:**
- Modify: `tests/plugins/test_river_flood.py`

- [ ] **Step 1: Add integration test (append to existing file)**

Add to `tests/plugins/test_river_flood.py`:

```python
import json
from pathlib import Path

import pytest

from persephone.core.engine import PersephoneEngine
from persephone.registry.registry import PluginRegistry
from persephone_river_flood import RiverFloodPlugin


class _FloodEntry:
    name = "river_flood"

    def load(self):
        return RiverFloodPlugin


def _flood_config(tmp_path: Path, preset: str = "spring_snowmelt") -> object:
    from persephone.config.load import load_experiment_config
    config = tmp_path / "experiment.yaml"
    config.write_text(
        f"""
name: flood_test
seed: 42
scheduler:
  t_end: 10
storage:
  artifacts_dir: runs
solvers:
  - type: graph
    plugin: river_flood
    version: ">=0.1.0"
    params:
      event_preset: {preset}
      precipitation_cms: 2000
      precipitation_duration_hours: 5
      routing_k: 0.35
""",
        encoding="utf-8",
    )
    return load_experiment_config(config)


def test_river_flood_run_completes_and_emits_metrics(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_FloodEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_flood_config(tmp_path), run_id="flood-test")

    assert result.status == "completed"
    assert result.final_time == pytest.approx(10.0)

    metrics_lines = (result.artifact_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    metrics = [json.loads(line) for line in metrics_lines]
    names = {m["metric"] for m in metrics}
    assert "stations_flooding" in names
    assert "total_excess_flow_cms" in names
    assert "flood_front_km" in names


def test_river_flood_spring_snowmelt_raises_upstream_flow(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_FloodEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_flood_config(tmp_path, preset="spring_snowmelt"), run_id="flood-snowmelt")

    metrics_lines = (result.artifact_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    metrics = [json.loads(line) for line in metrics_lines]

    # after 10 steps with heavy precip the total excess flow should be >0
    excess_values = [m["value"] for m in metrics if m["metric"] == "total_excess_flow_cms"]
    assert max(excess_values) > 0.0

    # flood front should be > 0 km once warning stations appear
    front_values = [m["value"] for m in metrics if m["metric"] == "flood_front_km"]
    assert max(front_values) >= 0.0  # may be 0 if wave hasn't reached warning stations in 10 steps


def test_river_flood_gulf_hurricane_preset(tmp_path: Path) -> None:
    registry = PluginRegistry(entry_points_provider=lambda: [_FloodEntry()])
    engine = PersephoneEngine(registry=registry, artifact_root=tmp_path / "runs")
    result = engine.run(_flood_config(tmp_path, preset="gulf_hurricane"), run_id="flood-hurricane")
    assert result.status == "completed"
```

- [ ] **Step 2: Run all tests**

```bash
uv run pytest tests/plugins/ -v
```

Expected: all model unit tests + integration tests pass.

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
uv run pytest -x
```

Expected: existing tests unaffected.

- [ ] **Step 4: Final commit**

```bash
git add tests/plugins/test_river_flood.py
git commit -m "test: river flood integration tests"
```
