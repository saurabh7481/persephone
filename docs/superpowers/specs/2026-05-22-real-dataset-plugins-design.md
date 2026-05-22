# Real Dataset Plugins: Airline Delay & River Flood Routing

**Date:** 2026-05-22
**Status:** Approved for implementation

## Overview

Two new Persephone plugins backed by real-world network data. Both use the `graph` paradigm with `map_network` as the primary view, giving geospatially anchored simulations on real topologies.

---

## Plugin 1: Airline Delay Propagation (`airline_delay`)

### Data

- **Source:** OpenFlights `airports.dat` + `routes.dat` (public domain)
- **Processing:** Filter to top-500 airports by outbound route count. Build undirected adjacency; weight each edge by number of shared routes between the pair (busier route = stronger delay coupling).
- **Bundled files:**
  - `airports.csv` — ~500 rows: `id, iata, name, city, country, lat, lon, route_count`
  - `routes.csv` — ~4,000 edges: `src_id, dst_id, weight`
- **Scale:** ~500 nodes, ~4,000 edges

### Paradigm & Timing

- Paradigm: `graph`
- Preferred dt: 1.0 (hours)
- Default run: 48 steps (48 simulated hours)

### State Arrays

| Key | shape | dtype | Description |
|-----|-------|-------|-------------|
| `delay_minutes` | (n_airports,) | float64 | Accumulated delay at each airport |
| `status` | (n_airports,) | int8 | 0=normal, 1=minor (15–45 min), 2=major (45–120 min), 3=disrupted (>120 min) |
| `edge_sources` | (n_edges,) | int64 | Graph structure |
| `edge_targets` | (n_edges,) | int64 | Graph structure |
| `edge_weights` | (n_edges,) | float64 | Route-count-normalised coupling strength |

### Simulation Model

Each step (1 simulated hour):

1. **Propagate** — for each airport with `delay_minutes > 0`, push `delay_minutes[src] × edge_weight × propagation_factor` to each neighbour's delay accumulator.
2. **Recover** — `delay_minutes *= (1 - recovery_rate)` applied globally (airports naturally drain delay).
3. **Reclassify** — recompute `status` from updated `delay_minutes` using fixed thresholds.

Initial shock: inject delay at 1–3 specified hub airports (default: JFK, LHR, DXB).

### Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `initial_airports` | list[str] | `["JFK","LHR","DXB"]` | IATA codes to shock at t=0 |
| `initial_delay_minutes` | number | 180 | Starting delay injected at each hub |
| `propagation_factor` | number | 0.3 | Fraction of delay pushed per edge per hour |
| `recovery_rate` | number | 0.15 | Fraction of delay recovered per hour |

### Metrics

| Metric | Kind | Headline |
|--------|------|---------|
| `delayed_airports` | scalar | — |
| `disrupted_airports` | scalar | yes |
| `total_delay_minutes` | scalar | yes |
| `max_delay_minutes` | scalar | — |
| `cascade_reach` | scalar | — | Cumulative count of unique airports that have ever been delayed (monotonically increasing) |

### Events

| Event | Trigger |
|-------|---------|
| `airport_disrupted` | Airport crosses 120 min threshold |
| `airport_recovered` | Airport drops back to normal |
| `hub_cascade` | Top-50 airport (by route count) becomes disrupted |

### Views

| View | Role |
|------|------|
| `map_network` | Primary — airports at real lat/lon, node colour = status |
| `network` | Secondary |

### Plugin Registration

```
name: airline_delay
package: persephone-plugin-airline-delay
entry point: persephone_airline_delay:AirlineDelayPlugin
```

---

## Plugin 2: River Flood Routing (`river_flood`)

### Data

- **Source:** Curated USGS Mississippi basin gauge network derived from NHD stream order data and published USGS reports.
- **Coverage:** ~120 major stream gauges from headwaters (upper Missouri, Minnesota River) to the Gulf of Mexico outlet.
- **Bundled files:**
  - `gauges.csv` — ~120 rows: `id, name, state, lat, lon, drainage_area_km2, normal_flow_cms, flood_stage_cms`
  - `network.csv` — ~119 directed edges: `upstream_id, downstream_id, travel_time_hours`
- **Scale:** ~120 nodes, ~119 directed edges (tree structure)

### Paradigm & Timing

- Paradigm: `graph`
- Preferred dt: 1.0 (hours)
- Default run: 120 steps (5 simulated days)

### State Arrays

| Key | shape | dtype | Description |
|-----|-------|-------|-------------|
| `storage_m3` | (n_stations,) | float64 | Current water volume in reach |
| `flow_cms` | (n_stations,) | float64 | Current outflow in cubic metres/second |
| `flood_status` | (n_stations,) | int8 | 0=normal, 1=watch, 2=warning, 3=flood |
| `flood_stage_cms` | (n_stations,) | float64 | Per-gauge flood threshold (fixed, from data) |
| `normal_flow_cms` | (n_stations,) | float64 | Per-gauge baseline flow (fixed, from data) |
| `edge_sources` | (n_edges,) | int64 | Upstream node indices |
| `edge_targets` | (n_edges,) | int64 | Downstream node indices |
| `edge_weights` | (n_edges,) | float64 | 1 / travel_time_hours |

### Simulation Model (Linear Reservoir Routing)

Each step (1 simulated hour):

1. **Inflow** — each station receives `sum(upstream_neighbours_flow_cms × edge_weight)`.
2. **Precipitation** — headwater nodes receive `precipitation_input_cms` for `precipitation_duration_hours` steps (driven by event preset or custom params).
3. **Route** — `outflow_cms = storage_m3 × routing_k`; `storage_m3 += (inflow_cms - outflow_cms) × 3600`.
4. **Classify** — compare `flow_cms` vs `flood_stage_cms`; set `flood_status`. Watch = 0.7×, warning = 0.9×, flood = 1.0×.

### Event Presets (bundled initial conditions)

| Preset | Injection points | Character |
|--------|-----------------|-----------|
| `spring_snowmelt` | Upper Missouri + Minnesota headwaters | Slow build, sustained |
| `gulf_hurricane` | Lower tributaries (Arkansas, Red River) simultaneously | Fast onset, southern basin |
| `custom` | User specifies station IDs + volume | Arbitrary |

### Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `event_preset` | string | `"spring_snowmelt"` | Which precipitation event to simulate |
| `precipitation_cms` | number | 500 | Added flow at injection points |
| `precipitation_duration_hours` | integer | 24 | How many steps the injection runs |
| `routing_k` | number | 0.35 | Linear reservoir coefficient (higher = faster drainage) |
| `custom_injection_stations` | list[int] | `[]` | Station IDs for custom preset |

### Metrics

| Metric | Kind | Headline |
|--------|------|---------|
| `stations_flooding` | scalar | yes |
| `stations_watch` | scalar | — |
| `total_excess_flow_cms` | scalar | yes |
| `peak_flow_cms` | scalar | — |
| `flood_front_km` | scalar | — | River-distance (km) from injection headwater to the farthest downstream station currently at warning or flood status |

### Events

| Event | Trigger |
|-------|---------|
| `flood_watch` | Station crosses watch threshold (0.7× flood stage) |
| `flood_stage_reached` | Station reaches flood stage |
| `peak_flow` | Station reaches its maximum flow this run |

### Views

| View | Role |
|------|------|
| `map_network` | Primary — gauges at real lat/lon, node colour = flood_status |
| `network` | Secondary — shows upstream→downstream direction |

### Plugin Registration

```
name: river_flood
package: persephone-plugin-river-flood
entry point: persephone_river_flood:RiverFloodPlugin
```

---

## File Structure (both plugins)

```
plugins/
  persephone-plugin-airline-delay/
    pyproject.toml
    src/persephone_airline_delay/
      __init__.py       # PluginManifest + SemanticManifest
      dataset.py        # CSV loading + data helpers
      model.py          # delay propagation math (pure functions)
      world.py          # World: init/reset state from CSVs
      solver.py         # Solver: step function
      observer.py       # Observer: metrics + events
      renderer.py       # Renderer: viz schema
      data/
        airports.csv
        routes.csv

  persephone-plugin-river-flood/
    pyproject.toml
    src/persephone_river_flood/
      __init__.py       # PluginManifest + SemanticManifest
      dataset.py        # CSV loading + preset helpers
      model.py          # linear reservoir routing (pure functions)
      world.py          # World: init/reset state
      solver.py         # Solver: step function
      observer.py       # Observer: metrics + events
      renderer.py       # Renderer: viz schema
      data/
        gauges.csv
        network.csv
```

## Build & Registration

Both plugins added to:
- `pyproject.toml` workspace `members` list
- `pyproject.toml` `[tool.uv.sources]` dependencies
- `pyproject.toml` main `dependencies` list

Each plugin's `pyproject.toml` registers via `[project.entry-points."persephone.plugins"]`.

## Out of Scope

- Live data fetching (static bundled data only)
- Muskingum routing or queuing theory models (can be added later)
- Plugins for other basins or airline regions
- Sweep/comparison runs (can be set up separately after plugins work)
