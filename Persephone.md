# Persephone — General-Purpose Simulation Platform
### Project Reference Document v0.1
> **Purpose of this document:** This file serves two roles simultaneously. First, it is a complete conceptual understanding of what Persephone is, why it is built the way it is, and how every layer works — so that any AI assistant or new developer can read it and immediately contribute meaningfully. Second, it is the canonical starting point for implementation: every code structure, interface contract, and technology choice documented here is the ground truth the codebase is built from. When in doubt about why something is structured a certain way, the answer is in this document.

---

## Table of Contents

1. [What Persephone Is](#1-what-persephone-is)
2. [The Five Simulation Paradigms](#2-the-five-simulation-paradigms)
3. [How the Paradigms Compose](#3-how-the-paradigms-compose)
4. [System Architecture — Five Layers](#4-system-architecture--five-layers)
5. [The Plugin System](#5-the-plugin-system)
6. [The Data Bus](#6-the-data-bus)
7. [The Multi-Rate Scheduler](#7-the-multi-rate-scheduler)
8. [The ODE Solver — Deep Dive](#8-the-ode-solver--deep-dive)
9. [The PDE Solver — Deep Dive](#9-the-pde-solver--deep-dive)
10. [The ABM Solver — Deep Dive](#10-the-abm-solver--deep-dive)
11. [The Graph Solver — Deep Dive](#11-the-graph-solver--deep-dive)
12. [The SDE Solver — Deep Dive](#12-the-sde-solver--deep-dive)
13. [Technology Stack](#13-technology-stack)
14. [Project File Structure](#14-project-file-structure)
15. [Data Schemas](#15-data-schemas)
16. [API Design](#16-api-design)
17. [Build & Run](#17-build--run)
18. [Phase Roadmap](#18-phase-roadmap)
19. [Simulation Domains & Data Sources](#19-simulation-domains--data-sources)
20. [Architecture Improvements & Fixes](#20-architecture-improvements--fixes)
21. [Glossary](#21-glossary)

---

## 1. What Persephone Is

Persephone is a **domain-agnostic, general-purpose simulation engine** designed for academic research, scientific computing, and AI agent workflows. It is not tied to any single domain — it is equally capable of running a fluid dynamics simulation, a disease spread model, a multi-agent reinforcement learning environment, or a custom user-defined system.

### Core design goals

| Goal | What it means in practice |
|---|---|
| Domain-agnostic | The engine knows nothing about physics, biology, or economics. All domain logic lives in plugins. |
| Composable | Multiple simulation paradigms can run simultaneously in one experiment, sharing state via a data bus. |
| Reproducible | Every run is versioned, seeded, and replayable. Results are never lost. |
| AI-native | AI agents can launch, observe, and steer simulations programmatically via the same API humans use. |
| Scalable | Runs on a laptop for prototyping; distributes across GPUs and MPI clusters for production. |

### What Persephone is NOT

- It is not a game engine (no real-time rendering, no physics engine like Bullet or PhysX)
- It is not a domain-specific tool (not GROMACS, not NetLogo, not MATLAB Simulink)
- It is not a data pipeline (it produces time-series data, but is not ETL)

---

## 2. The Five Simulation Paradigms

Persephone supports five fundamental simulation paradigms. Each answers a different kind of question about a system. They are not competing — they are complementary lenses on the same reality.

### 2.1 ODE — Ordinary Differential Equations

**The question it answers:** How do a small number of quantities evolve over time, given that their rate of change depends on their current value?

**The state:** A fixed-length vector of real numbers. For example `[prey_count, predator_count]` or `[viral_load, immune_response]`.

**The update rule:** The plugin provides a function `f(x, t) → dx/dt`. The engine integrates this forward in time.

**Mental model:** You know the slope at the current point. You march along that slope for a tiny `dt`. The slope changes, you recompute, you march again. Repeat.

**Strengths:** Exact, well-understood numerics. Fast for low-dimensional systems. Rich tooling (scipy, diffeq).

**Weaknesses:** No spatial dimension. No individuals. All dynamics lumped into aggregate quantities.

**Canonical examples:** Predator-prey (Lotka-Volterra), SIR epidemic without geography, viral mutation rates, pharmacokinetics, chemical reaction kinetics.

---

### 2.2 PDE — Partial Differential Equations

**The question it answers:** How does a quantity vary across space *and* time, given that the rate of change at each point depends on its neighbors?

**The state:** A field — a 2D or 3D grid (or mesh) where each cell holds one or more values. For example, a 512×512 temperature grid, or a 3D pressure field.

**The update rule:** At each cell, compute the Laplacian (the average difference from neighbors) and use it to update the cell's value. For heat diffusion:

```
∂u/∂t = D · ∇²u

where ∇²u[i,j] = u[i+1,j] + u[i-1,j] + u[i,j+1] + u[i,j-1] − 4·u[i,j]
```

**Mental model:** A grid of cells. Each cell looks at its four neighbors and adjusts itself. Repeat for every cell, simultaneously, every tick.

**Strengths:** Captures spatial dynamics. Foundation of fluid, heat, wave, and diffusion simulations.

**Weaknesses:** Expensive for large grids. Stability constraints limit step size (CFL condition). Irregular geometries require finite elements (complex).

**Canonical examples:** Heat diffusion, fluid flow (Navier-Stokes), aerosol spread, groundwater contamination, electromagnetic fields.

**CFL condition (critical constraint):** The time step `dt` must satisfy `dt ≤ (dx²) / (2D)` where `dx` is the grid spacing and `D` is the diffusion coefficient. Violating this causes the simulation to explode (values go to infinity). This is why PDE solvers impose a maximum `dt` on the multi-rate scheduler.

---

### 2.3 ABM — Agent-Based Model

**The question it answers:** What collective behavior emerges when many individuals each follow simple local rules?

**The state:** A list of agent objects. Each agent has its own position, velocity, internal state, and memory.

**The update rule:** Each tick, every agent calls its `tick(world)` method. It reads local information (nearby agents, field values at its position), makes a decision, and updates its own state.

**Mental model:** A list of objects, each with a `tick()` method. No global formula. Macro behavior emerges from micro rules.

**Strengths:** Natural for modeling individual decision-making, heterogeneous populations, emergent behavior. Most intuitive for software engineers.

**Weaknesses:** Expensive for very large populations (O(N) per tick, O(N²) for naive neighbor search). Emergent behavior is hard to predict analytically.

**Canonical examples:** Pedestrian evacuation, flocking (boids), social contagion, market microstructure, epidemics with behavioral response, ecological foraging.

**Spatial indexing (critical for performance):** Naive neighbor search is O(N²). A grid hash divides the world into cells; each agent registers in its cell. Neighbor query checks only the surrounding 9 cells — O(1) lookup, O(k) iteration where k is local density. Required for any simulation with more than ~1,000 agents.

---

### 2.4 Graph / Network Simulation

**The question it answers:** How do things spread, flow, or cascade through a network of relationships?

**The state:** A graph: nodes with state, edges with weights or transmission probabilities.

**The update rule:** For each edge `(u, v)`, if `u` is in state A, transition `v` to state B with probability `p`. The topology of the graph is as important as the rules.

**Mental model:** A social network, supply chain, or contact network. The structure of who connects to whom determines the dynamics at least as much as the transition rules.

**Strengths:** Models topology-dependent dynamics that ODEs cannot capture. Natural for social systems, supply chains, power grids, biological pathways.

**Weaknesses:** Scalability for very large graphs. Defining meaningful edge weights requires domain expertise.

**Canonical examples:** Disease spread on contact networks, information cascade on social graphs, supply chain disruption, neuronal firing, financial contagion.

---

### 2.5 SDE — Stochastic Differential Equations

**The question it answers:** How does a small number of quantities evolve over time when their dynamics contain both a deterministic trend *and* intrinsic random noise that cannot be averaged away?

**The state:** A fixed-length vector of real numbers — identical in shape to ODE state. For example `[price, volatility]` or `[gene_expression_level, noise_amplitude]`.

**The update rule:** The plugin provides two functions: a drift `f(x, t) → dx/dt` (the ODE part) and a diffusion `g(x, t) → σ` (the noise amplitude). The engine integrates the Itô SDE:

```
dx = f(x, t) dt  +  g(x, t) dW
```

where `dW` is a Wiener process increment drawn from `N(0, dt)` each step.

**Mental model:** Like an ODE, but every step you also nudge the state by a random amount whose size is controlled by `g`. Over many runs with different random seeds, you get a distribution of trajectories, not a single curve.

**Strengths:** Captures intrinsic stochasticity (ion channel gating, gene expression bursting, price diffusion) that ODEs smooth over. Naturally produces distributions, confidence intervals, and rare-event statistics.

**Weaknesses:** Results are stochastic — a single run is meaningless; you need an ensemble (many runs with different seeds). Numerical stability requires small `dt` for explicit methods. Stiff SDEs require implicit schemes (not yet standard).

**Canonical examples:** Financial asset price models (Black-Scholes, Heston), gene regulatory networks with transcriptional noise, ion channel gating (Langevin approximation to Markov chains), epidemic models with demographic stochasticity, turbulent velocity fluctuations.

**Key distinction from ODE:** An ODE with the same `f(x,t)` and seed 42 always produces the same trajectory. An SDE with the same `f(x,t)` produces a different trajectory every run — the randomness is intrinsic to the model, not just initialization.

---

## 3. How the Paradigms Compose

The power of Persephone is that these five paradigms can run simultaneously in one experiment, sharing state through the data bus.

### Concrete example: City epidemic simulation

| Paradigm | Role | Reads from bus | Writes to bus |
|---|---|---|---|
| ODE | Viral mutation dynamics | — | `viral_fitness` |
| PDE | Aerosol diffusion across the city map | — | `aerosol_grid` |
| ABM | Individual human behavior (masking, travel) | `aerosol_grid`, `viral_fitness` | `agent_states` |
| Graph | Infection propagation across contact network | `agent_states`, `viral_fitness` | `infection_map` |

No single paradigm can model this alone:
- The ODE captures how the virus evolves but has no geography and no individuals
- The PDE models how aerosols spread spatially but has no behavior
- The ABM models individual decisions but needs the field data to decide rationally
- The Graph propagates infections but needs to know who is susceptible

Together, the emergent output — infection curves shaped by behavioral response, spatial hotspot formation, wave timing — is something no single equation could produce.

### The data bus is the enabling mechanism

Solvers never call each other. The ODE solver doesn't know an ABM exists. It only knows how to write `viral_fitness` to the bus. The ABM only knows how to read `viral_fitness` from the bus. This decoupling is what makes the system composable — you can add, remove, or swap any solver without touching the others.

---

## 4. System Architecture — Five Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5 — AI Agent & User Interface                        │
│  Svelte web UI · Agent SDK · Notebook integration           │
│  REST / WebSocket / CLI endpoints                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 4 — Experiment Orchestration                         │
│  Run manager · Parameter sweeps · Multi-sim pipelines       │
│  Results versioning · Diff & replay                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 3 — Simulation Engine Core (Python/Rust)             │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Solver      │ │ Multi-rate   │ │ Data bus (Redis /    │ │
│  │ kernel      │ │ scheduler    │ │ in-process pub/sub)  │ │
│  │ ODE·PDE·ABM │ │              │ │                      │ │
│  │ Graph       │ │              │ │                      │ │
│  └─────────────┘ └──────────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Layer 2 — Domain Plugin System                             │
│  Plugin SDK · WASM sandbox · First-party plugins            │
│  Physics · Climate · Biology · Economics · AI/RL · Custom   │
├─────────────────────────────────────────────────────────────┤
│  Layer 1 — Compute Backend                                  │
│  CPU threadpool · GPU/CUDA · MPI cluster · WASM sandbox     │
├─────────────────────────────────────────────────────────────┤
│  Storage & Observability                                     │
│  ClickHouse (metrics/events) · TimescaleDB (time-series)    │
│  Redis (bus) · S3/local (artefacts) · Live metrics          │
└─────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

**Layer 1 — Compute backend:** Raw execution. CPU thread pools for parallelism across agents and grid cells. CUDA kernels for large PDE grids. MPI harness for distributing parameter sweeps across nodes. The engine dispatches work here; it never blocks waiting for results.

**Layer 2 — Domain plugin system:** Each plugin is a self-contained package implementing the four-interface contract (`World`, `Solver`, `Observer`, `Renderer`). First-party plugins are shipped with Persephone. Community plugins are sandboxed in WASM. The Plugin SDK provides base classes, testing utilities, and documentation templates.

**Layer 3 — Engine core:** The scheduler, the time-step loop, the inter-simulation data bus. Handles the different solver paradigms, manages synchronization points, routes data between solvers. Written in Python initially; performance-critical paths ported to Rust.

**Layer 4 — Experiment orchestration:** A researcher defines an experiment as a YAML/JSON config. The orchestrator fans it out: multiple runs with different parameters, different random seeds, different solver combinations. Results are versioned; every run is reproducible from its config + seed alone.

**Layer 5 — AI agent & user interface:** The Svelte frontend for human researchers. The Python/TypeScript SDK for AI agents. The CLI for scripting. All three talk to the same Hono.js API layer, which proxies to the engine. An AI agent calls `persephone.run(config)` the same way a human presses "Run" in the UI.

---

## 5. The Plugin System

### Design Philosophy: Plugins Are External Packages

Plugins do not live inside the Persephone repository. Each plugin is an independently versioned Python package published to PyPI (or a private registry). The engine discovers installed plugins at startup via Python's entry points mechanism — zero hardcoding, zero config file edits required.

This matters for three reasons:

- **Core stability:** A broken plugin cannot crash the engine's import tree. Discovery is isolated in a try/catch per plugin.
- **Independent versioning:** `persephone-plugin-wildfire v2.1` can be installed without upgrading Persephone core. Plugins follow their own release cadence.
- **Community ecosystem:** Anyone can publish `pip install persephone-plugin-<domain>` and it works immediately. The engine does not need to know about it in advance.

### The Three-Package Architecture

```
persephone-sdk          ← pip install persephone-sdk
  persephone_sdk/
    plugin.py         ← PluginManifest dataclass + World/Solver/Observer/Renderer ABCs
    testing.py        ← PluginTestHarness (standard compliance test suite)
    validators.py     ← bus channel schema + shape + unit validators

persephone              ← the core engine (depends on persephone-sdk, NOT on any plugin)
  engine/
    core/
      registry.py     ← discovers plugins via entry_points(); owns no domain logic

persephone-plugin-*     ← each plugin is its own package, depends on persephone-sdk
  pyproject.toml      ← declares entry point; the only integration point with the engine
```

The engine never imports plugin code directly. It calls `importlib.metadata.entry_points()`, loads each discovered plugin class, calls the static `manifest()` method, and stores the manifest. All engine↔plugin communication goes through the four ABCs defined in the SDK.

### Entry Point Declaration (plugin author side)

A plugin registers itself by adding one line to its own `pyproject.toml`. No changes to Persephone core needed.

```toml
# persephone-plugin-wildfire/pyproject.toml

[project]
name = "persephone-plugin-wildfire"
version = "1.0.0"
dependencies = ["persephone-sdk>=0.3", "rasterio>=1.3", "numpy"]

[project.entry-points."persephone.plugins"]
wildfire_spread = "persephone_wildfire:WildfirePlugin"
#  ↑ entry point name    ↑ import path : class name
#  This name is what goes in experiment YAML as `plugin: wildfire_spread`
```

Installation is a single command:

```bash
pip install persephone-plugin-wildfire
# Plugin is now available to any Persephone engine in this environment.
# No config edits. No registry updates. No core repo changes.
```

### Engine-Side Discovery

```python
# engine/core/registry.py

from importlib.metadata import entry_points
import logging

logger = logging.getLogger(__name__)

class PluginRegistry:
    def __init__(self):
        self._plugins: dict[str, 'PluginManifest'] = {}

    def discover(self):
        """
        Scan all installed packages for 'persephone.plugins' entry points.
        Called once at engine startup. A broken plugin is logged and skipped;
        it never crashes the engine.
        """
        eps = entry_points(group="persephone.plugins")
        for ep in eps:
            try:
                plugin_class = ep.load()
                manifest = plugin_class.manifest()   # static method, no instantiation
                self._validate_sdk_version(manifest)
                self._plugins[ep.name] = manifest
                logger.info(f"Loaded plugin: {ep.name} v{manifest.version}")
            except Exception as e:
                logger.warning(f"Plugin '{ep.name}' failed to load: {e}")

    def get(self, name: str) -> 'PluginManifest':
        if name not in self._plugins:
            raise KeyError(
                f"Plugin '{name}' not installed. "
                f"Run: pip install persephone-plugin-{name}"
            )
        return self._plugins[name]

    def list_all(self) -> list[dict]:
        return [
            {'name': k, 'version': v.version, 'paradigm': v.paradigm}
            for k, v in self._plugins.items()
        ]

    def _validate_sdk_version(self, manifest):
        from persephone_sdk import __version__ as sdk_version
        from packaging.version import Version
        if Version(sdk_version) < Version(manifest.sdk_min_version):
            raise RuntimeError(
                f"Plugin requires persephone-sdk>={manifest.sdk_min_version}, "
                f"installed: {sdk_version}"
            )
```

### The Plugin Manifest and Four-Interface Contract

Every plugin must implement exactly four interfaces (ABCs from `persephone-sdk`) and expose them via a static `manifest()` method.

```python
# persephone_sdk/plugin.py

from dataclasses import dataclass
from typing import Type
from abc import ABC, abstractmethod
import numpy as np

# ── The four interfaces ──────────────────────────────────────────────────────

class World(ABC):
    """Defines the shape of the simulation's state and how to initialize it."""

    @abstractmethod
    def schema(self) -> dict:
        """
        Returns a description of the state space as {key: shape} pairs.
        Example: {'position': (N, 2), 'velocity': (N, 2), 'infected': (N,)}
        """
        ...

    @abstractmethod
    def init(self, params: dict, seed: int) -> dict:
        """
        Returns the initial world state as a dict of numpy arrays.
        Must be deterministic given the same params and seed.
        """
        ...

    @abstractmethod
    def reset(self) -> dict:
        """Returns the world to its initial state. Used between parameter sweep runs."""
        ...


class Solver(ABC):
    """The computational core. Advances state by one time interval."""

    @abstractmethod
    def step(self, state: dict, dt: float, bus: 'DataBus') -> tuple[dict, float]:
        """
        Advance the world state by at most dt time units.

        Returns:
            (new_state, actual_dt_advanced)
            actual_dt_advanced may be less than dt if the solver hit a constraint.
        """
        ...

    @property
    @abstractmethod
    def preferred_dt(self) -> float:
        """
        The solver's preferred synchronization interval.
        ODE/SDE: large (self-adapts internally)
        PDE: bounded by CFL condition
        ABM: one logical tick (e.g. 1 day, 1 second)
        Graph: one logical event cycle
        """
        ...

    @property
    def is_stiff(self) -> bool:
        """Override to True if the system is stiff (triggers implicit solver)."""
        return False

    @property
    def is_stochastic(self) -> bool:
        """Override to True for SDE plugins (enables ensemble run mode)."""
        return False


class Observer(ABC):
    """Watches the state after each tick and emits metrics/events."""

    @abstractmethod
    def observe(self, state: dict, t: float, run_id: str) -> list[dict]:
        """
        Called after each successful solver step.
        Returns a list of metric records:
        [{'metric': str, 'value': float, 't': float, 'tags': dict}, ...]
        """
        ...

    def on_event(self, event: str, payload: dict, t: float):
        """Called on discrete events (threshold crossed, agent death, etc.). Default: no-op."""
        pass


class Renderer(ABC):
    """Provides visualization hints. Read-only and stateless."""

    @abstractmethod
    def viz_schema(self) -> dict:
        """
        Describes how to visualize the state. Used by the UI; never changes state.
        Example:
        {
            'type': 'field_2d',
            'channel': 'temperature',
            'colormap': 'plasma',
            'overlay': {'type': 'agents', 'channel': 'agent_positions'}
        }
        """
        ...


# ── The manifest ─────────────────────────────────────────────────────────────

@dataclass
class PluginManifest:
    name: str               # matches the entry point name in pyproject.toml
    version: str            # semver
    paradigm: str           # 'ode' | 'pde' | 'abm' | 'graph' | 'sde' | 'hybrid'
    world:    Type[World]
    solver:   Type[Solver]
    observer: Type[Observer]
    renderer: Type[Renderer]
    bus_reads:  list[str]   # channels this plugin reads from the bus (declared, not enforced at runtime)
    bus_writes: list[str]   # channels this plugin writes to the bus
    default_params: dict    # shown in UI, used by CLI if not overridden
    sdk_min_version: str    # engine refuses to load plugins below this SDK version
```

### Why these four interfaces?

- `World` separates initialization from computation. A parameter sweep calls `reset()` between runs without reinstantiating anything.
- `Solver` is the only interface that touches time. Everything time-related is here.
- `Observer` is the only interface that writes to storage. Solvers never touch the database — they hand data to the Observer, which decides what to record.
- `Renderer` is read-only and stateless. The UI calls it to understand how to display data; it never changes simulation state.

The `bus_reads` and `bus_writes` declarations in the manifest enable *static validation*: before a multi-plugin experiment starts, the engine can check that every channel a plugin reads is written by some other active plugin, and warn the researcher about missing connections.

### Plugin Test Harness (SDK-provided)

Every plugin gets a standard compliance suite for free. Plugin authors run this; it is not part of the engine.

```python
# persephone_sdk/testing.py

class PluginTestHarness:
    """
    Standard compliance test suite for any Persephone plugin.
    Usage in the plugin's own test suite:
        from persephone_sdk.testing import PluginTestHarness
        harness = PluginTestHarness(MyPlugin)
        harness.run_all()
    """

    def test_schema_matches_init_output(self, plugin):
        state = plugin.world.init(plugin.manifest.default_params, seed=42)
        schema = plugin.world.schema()
        for key, shape in schema.items():
            assert key in state, f"Key '{key}' declared in schema but missing from init()"
            assert state[key].shape == shape, f"Shape mismatch for '{key}'"

    def test_solver_step_is_finite(self, plugin):
        state = plugin.world.init(plugin.manifest.default_params, seed=42)
        bus = MockDataBus()
        new_state, dt_advanced = plugin.solver.step(state, dt=1.0, bus=bus)
        for key, arr in new_state.items():
            assert np.all(np.isfinite(arr)), f"Non-finite values in '{key}' after step()"

    def test_reset_returns_identical_state(self, plugin):
        s1 = plugin.world.init(plugin.manifest.default_params, seed=42)
        s2 = plugin.world.reset()
        for key in s1:
            np.testing.assert_array_equal(s1[key], s2[key])

    def test_bus_writes_match_declared_channels(self, plugin):
        bus = SpyDataBus()  # records all write() calls
        state = plugin.world.init(plugin.manifest.default_params, seed=42)
        plugin.solver.step(state, dt=1.0, bus=bus)
        for ch in bus.written_channels:
            assert ch in plugin.manifest.bus_writes, \
                f"Plugin wrote to undeclared bus channel '{ch}'"

    def test_manifest_sdk_version_present(self, plugin):
        assert plugin.manifest.sdk_min_version, "sdk_min_version must be set"
```

### Experiment Config (plugin reference)

The YAML config references plugins by their entry point name only. The engine resolves the rest.

```yaml
solvers:
  - type: pde
    plugin: wildfire_spread        # ← entry point name; engine calls registry.get()
    version: ">=1.0"               # engine refuses to run if installed version is lower
    params:
      fuel_map: data/landfire.tif
      wind_speed: 8.0
      wind_direction: 225
```

---

## 6. The Data Bus

The data bus is a named key-value store that all active solvers read from and write to after each step. It is the only mechanism by which solvers communicate.

### Design principles

- **Named channels:** Data is addressed by string name (`'temperature_field'`, `'agent_positions'`, `'viral_fitness'`). No direct solver-to-solver references.
- **Write-then-read ordering:** Within one tick, all solvers write their outputs from the *previous* step's reads. No solver reads another solver's output from the *current* tick. This prevents ordering-dependent results.
- **Type-checked:** Channels have declared types and shapes. Writing wrong-shaped data raises immediately.
- **Versioned:** Each write stamps a `(run_id, tick, solver_id)` key. The Observer can reconstruct the full history.

### Implementation

**Development / single-process:** Python dict with a read-write lock per channel. Zero latency. Suitable for local runs.

**Production / multi-process:** Redis pub/sub. Each solver is a separate process or thread. The bus is a Redis instance. Channels map to Redis keys with TTL. Suitable for distributed parameter sweeps.

The snippet below is intentionally simple. Production Redis/network backends must use the double-buffered contract described in [Architecture Improvements & Fixes](#203-fix-the-data-bus-should-be-double-buffered) and must not use `pickle` for untrusted data.

```python
class DataBus:
    def __init__(self, backend: str = 'memory'):
        # backend: 'memory' | 'redis'
        self._store = {}
        self._backend = backend
        if backend == 'redis':
            import redis
            self._redis = redis.Redis(host='localhost', port=6379, db=0)

    def write(self, channel: str, value: np.ndarray, solver_id: str, tick: int):
        record = {'value': value, 'solver_id': solver_id, 'tick': tick}
        if self._backend == 'memory':
            self._store[channel] = record
        else:
            import pickle
            self._redis.set(channel, pickle.dumps(record))

    def read(self, channel: str) -> np.ndarray | None:
        if self._backend == 'memory':
            rec = self._store.get(channel)
            return rec['value'] if rec else None
        else:
            import pickle
            raw = self._redis.get(channel)
            return pickle.loads(raw)['value'] if raw else None
```

---

## 7. The Multi-Rate Scheduler

Different solvers want to run at different time resolutions:

| Solver | Typical preferred_dt | Reason |
|---|---|---|
| ODE | Large (adapts internally) | Adaptive sub-stepping handles accuracy |
| PDE | Small (CFL-bounded) | Grid stability constraint |
| ABM | Medium (one logical event) | One "day" or "second" per tick |
| Graph | Large (one event cycle) | Propagation is discrete, not continuous |

The multi-rate scheduler manages this without forcing all solvers to run at the slowest rate.

### Algorithm: operator splitting

```
sync_interval = min(preferred_dt for all active solvers)

while t < t_end:
    # Fan out: run all solvers in parallel up to sync_interval
    results = parallel_map(
        lambda solver: solver.step(state, sync_interval, bus),
        active_solvers
    )

    # Merge: reconcile all outputs
    new_state = merge(results, coupling_rules)

    # Observe: emit metrics
    for observer in observers:
        observer.observe(new_state, t, run_id)

    t += sync_interval
    bus.flush()   # mark current tick complete
```

### Coupling rules in merge

When two solvers write to the same channel, a coupling rule resolves the conflict:

```python
COUPLING_RULES = {
    'infection_map': 'sum',       # additive: combine contributions
    'temperature':   'mean',      # average: spatial averaging
    'agent_states':  'last',      # last-writer wins: ABM owns agent state
    'viral_fitness': 'max',       # max: most virulent strain dominates
}
```

Coupling rules are declared in the experiment config, not hardcoded in the engine.

---

## 8. The ODE Solver — Deep Dive

### What it does

Integrates `dx/dt = f(x, t)` forward in time using adaptive step-size control.

### The algorithm: RK45 (Dormand-Prince)

Four key methods, from simplest to production:

**Euler (never use in production):**
```python
x_next = x + f(x, t) * dt
# Error: O(dt) — halving dt halves error. Too slow to converge.
```

**RK4 (good for fixed-dt non-stiff systems):**
```python
k1 = f(x,           t)
k2 = f(x + k1*dt/2, t + dt/2)
k3 = f(x + k2*dt/2, t + dt/2)
k4 = f(x + k3*dt,   t + dt)
x_next = x + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)
# Error: O(dt⁴) — halving dt reduces error by 16×.
```

**RK45 adaptive (use this):**
Runs two estimates (4th and 5th order) using the same 6 derivative evaluations. Compares them to estimate local error. Accepts the step if `error < rtol * |x| + atol`, shrinks `dt` and retries otherwise. Grows `dt` for next step if error was well below tolerance.

**BDF/Radau (for stiff systems):**
Implicit methods that solve a nonlinear equation at each step. Unconditionally stable. Required when the plugin sets `is_stiff = True`.

### The engine-level ODE solver wrapper

```python
from scipy.integrate import solve_ivp
import numpy as np

class ODESolverWrapper:
    def __init__(self, plugin_solver, world_state: dict):
        self.plugin = plugin_solver
        self.x = self._flatten(world_state)
        self.t = 0.0
        self.method = 'Radau' if plugin_solver.is_stiff else 'RK45'

    def _flatten(self, state: dict) -> np.ndarray:
        """Flatten the state dict into a 1D numpy array for scipy."""
        return np.concatenate([v.ravel() for v in state.values()])

    def _unflatten(self, x: np.ndarray, template: dict) -> dict:
        """Reconstruct the state dict from a 1D array."""
        result, idx = {}, 0
        for k, v in template.items():
            size = v.size
            result[k] = x[idx:idx+size].reshape(v.shape)
            idx += size
        return result

    def step(self, state: dict, dt_max: float, bus: DataBus) -> tuple[dict, float]:
        start_t = self.t
        external = {
            'temperature': bus.read('temperature_field'),
            'aerosol':     bus.read('aerosol_grid'),
        }

        def f(t, x):
            s = self._unflatten(x, state)
            ds = self.plugin.derivative(s, t, external)
            return self._flatten(ds)

        result = solve_ivp(
            f,
            t_span=[self.t, self.t + dt_max],
            y0=self.x,
            method=self.method,
            rtol=1e-6,
            atol=1e-9,
            dense_output=True,
        )

        self.x = result.y[:, -1]
        self.t = result.t[-1]

        new_state = self._unflatten(self.x, state)
        bus.write('viral_fitness', new_state.get('viral_fitness', np.array([0.0])),
                  solver_id='ode', tick=int(self.t))

        return new_state, self.t - start_t
```

### Tuning parameters

| Parameter | Typical value | Effect |
|---|---|---|
| `rtol` | `1e-6` | Relative tolerance. Tighter = slower, more accurate. |
| `atol` | `1e-9` | Absolute tolerance near zero. Set to `rtol × typical_scale`. |
| `dt_max` | Sync interval | How often the ODE hands off to the bus. Set to the timescale of the coupling, not the fastest dynamics. |
| `method` | `'RK45'` or `'Radau'` | RK45 for non-stiff; Radau for stiff. Stiffness detected by slow convergence of RK45. |

---

## 9. The PDE Solver — Deep Dive

### What it does

Advances a spatial field forward in time using finite differences on a regular grid.

### Core update — finite difference Laplacian

```python
import numpy as np

def laplacian_2d(u: np.ndarray) -> np.ndarray:
    """
    Compute ∇²u using finite differences on a 2D grid.
    Boundary cells are handled with zero-flux (Neumann) conditions by default.
    """
    return (
        np.roll(u, 1, axis=0) + np.roll(u, -1, axis=0) +
        np.roll(u, 1, axis=1) + np.roll(u, -1, axis=1) -
        4 * u
    )

def pde_step(u: np.ndarray, D: float, dt: float, dx: float) -> np.ndarray:
    """One explicit Euler step of the heat equation ∂u/∂t = D∇²u."""
    return u + dt * D * laplacian_2d(u) / (dx ** 2)
```

### CFL stability constraint

```python
def max_dt(D: float, dx: float, ndim: int = 2) -> float:
    """
    Maximum stable time step for explicit finite differences.
    Violating this causes values to grow without bound.
    """
    return (dx ** 2) / (2 * ndim * D)
```

The PDE solver enforces this internally. It declares `preferred_dt = max_dt(D, dx)` so the scheduler never gives it a window larger than it can handle.

### GPU acceleration with CuPy

For large grids (>512×512), the inner loop can be offloaded to GPU:

```python
try:
    import cupy as cp
    xp = cp    # GPU array
except ImportError:
    xp = np    # CPU array fallback

def pde_step_gpu(u, D, dt, dx):
    return u + dt * D * laplacian_2d(u) / (dx ** 2)
    # All operations are identical — CuPy mirrors the NumPy API.
    # The array lives on GPU; no data transfer per step.
```

---

## 10. The ABM Solver — Deep Dive

### What it does

Advances a population of agents by calling each agent's `tick()` method in turn (or in parallel).

### Agent base class

```python
from dataclasses import dataclass, field
from typing import Protocol
import numpy as np

@dataclass
class Agent:
    id: int
    position: np.ndarray          # shape (2,) for 2D, (3,) for 3D
    velocity: np.ndarray
    state: str = 'susceptible'    # domain-specific state label
    memory: dict = field(default_factory=dict)

    def tick(self, world: 'ABMWorld', bus: 'DataBus', dt: float) -> None:
        """Override in domain plugin. Reads world/bus, mutates self."""
        raise NotImplementedError
```

### Spatial index — grid hash

```python
class SpatialHash:
    def __init__(self, cell_size: float):
        self.cell_size = cell_size
        self._grid: dict[tuple, list] = {}

    def _key(self, pos: np.ndarray) -> tuple:
        return tuple((pos // self.cell_size).astype(int))

    def insert(self, agent: Agent):
        k = self._key(agent.position)
        self._grid.setdefault(k, []).append(agent)

    def neighbors(self, pos: np.ndarray, radius: float) -> list[Agent]:
        results = []
        r = int(np.ceil(radius / self.cell_size))
        base = (pos // self.cell_size).astype(int)
        for dx in range(-r, r+1):
            for dy in range(-r, r+1):
                results.extend(self._grid.get(
                    (base[0]+dx, base[1]+dy), []
                ))
        return results

    def rebuild(self, agents: list[Agent]):
        self._grid.clear()
        for a in agents:
            self.insert(a)
```

### ABM solver step with numba JIT

```python
from numba import njit, prange
import numpy as np

@njit(parallel=True)
def _tick_positions(positions, velocities, dt, world_size):
    """JIT-compiled position update for all agents."""
    n = positions.shape[0]
    for i in prange(n):
        positions[i] += velocities[i] * dt
        # Wrap at world boundaries
        positions[i] %= world_size
    return positions
```

---

## 11. The Graph Solver — Deep Dive

### What it does

Propagates state transitions across a network of nodes connected by weighted edges.

### Core data structure

```python
import numpy as np
from scipy.sparse import csr_matrix

class ContactGraph:
    def __init__(self, n_nodes: int):
        self.n = n_nodes
        self.states = np.full(n_nodes, 'S', dtype='U1')  # S / I / R
        self.edges: list[tuple[int, int, float]] = []     # (u, v, weight)

    def add_edge(self, u: int, v: int, weight: float = 1.0):
        self.edges.append((u, v, weight))

    def to_sparse(self) -> csr_matrix:
        rows = [u for u, v, _ in self.edges]
        cols = [v for u, v, _ in self.edges]
        data = [w for _, _, w in self.edges]
        return csr_matrix((data, (rows, cols)), shape=(self.n, self.n))
```

### Propagation step (vectorized)

```python
def graph_step(graph: ContactGraph, p_infect: float, p_recover: float,
               rng: np.random.Generator, bus: DataBus) -> ContactGraph:
    viral_fitness = bus.read('viral_fitness')
    effective_p = p_infect * (1 + viral_fitness[0] if viral_fitness is not None else 1.0)

    new_states = graph.states.copy()
    infected_mask = graph.states == 'I'

    for u, v, w in graph.edges:
        if graph.states[u] == 'I' and graph.states[v] == 'S':
            if rng.random() < effective_p * w:
                new_states[v] = 'I'
        if graph.states[v] == 'I' and graph.states[u] == 'S':
            if rng.random() < effective_p * w:
                new_states[u] = 'I'

    recover_mask = (graph.states == 'I') & (rng.random(graph.n) < p_recover)
    new_states[recover_mask] = 'R'

    graph.states = new_states
    bus.write('infection_map', (graph.states == 'I').astype(np.float32),
              solver_id='graph', tick=0)
    return graph
```

---

## 12. The SDE Solver — Deep Dive

### What it does

Integrates `dx = f(x,t) dt + g(x,t) dW` forward in time — an ODE drift term plus a noise term whose magnitude is state- and time-dependent. Every call to `step()` produces a different trajectory (by design); results are only meaningful as ensembles over many runs.

### The two numerical methods

**Euler-Maruyama (default, non-stiff):**

```python
import numpy as np

def euler_maruyama_step(x: np.ndarray, t: float, dt: float,
                        drift_fn, diffusion_fn,
                        rng: np.random.Generator) -> np.ndarray:
    """
    One step of the Euler-Maruyama scheme.
    Converges with strong order 0.5 and weak order 1.0.
    Sufficient for most financial and biological SDE applications.
    """
    dW = rng.standard_normal(x.shape) * np.sqrt(dt)   # Wiener increment
    return x + drift_fn(x, t) * dt + diffusion_fn(x, t) * dW
```

**Milstein (higher order, for scalar or diagonal noise):**

```python
def milstein_step(x: np.ndarray, t: float, dt: float,
                  drift_fn, diffusion_fn, diffusion_derivative_fn,
                  rng: np.random.Generator) -> np.ndarray:
    """
    Milstein scheme. Strong order 1.0.
    Requires the derivative of g with respect to x: dg/dx.
    Use when noise is multiplicative (g depends on x) and accuracy matters.
    """
    dW = rng.standard_normal(x.shape) * np.sqrt(dt)
    g   = diffusion_fn(x, t)
    dgdx = diffusion_derivative_fn(x, t)
    return x + drift_fn(x, t) * dt + g * dW + 0.5 * g * dgdx * (dW**2 - dt)
```

### The engine-level SDE solver wrapper

```python
class SDESolverWrapper:
    def __init__(self, plugin_solver, world_state: dict, seed: int):
        self.plugin = plugin_solver
        self.x = self._flatten(world_state)
        self.t = 0.0
        self.rng = np.random.default_rng(seed)
        # Method selection: Milstein if plugin declares diffusion_derivative()
        self.method = 'milstein' if hasattr(plugin_solver, 'diffusion_derivative') \
                      else 'euler_maruyama'

    def step(self, state: dict, dt_max: float, bus: DataBus) -> tuple[dict, float]:
        # SDE uses fixed small dt (no adaptive step size — error control
        # for SDEs requires different techniques than for ODEs)
        dt = min(dt_max, self.plugin.preferred_dt)

        if self.method == 'milstein':
            x_new = milstein_step(
                self.x, self.t, dt,
                self.plugin.drift, self.plugin.diffusion,
                self.plugin.diffusion_derivative, self.rng
            )
        else:
            x_new = euler_maruyama_step(
                self.x, self.t, dt,
                self.plugin.drift, self.plugin.diffusion, self.rng
            )

        self.x = x_new
        self.t += dt
        new_state = self._unflatten(x_new, state)

        # Write declared outputs to bus
        for channel in self.plugin.manifest.bus_writes:
            if channel in new_state:
                bus.write(channel, new_state[channel], solver_id='sde', tick=int(self.t))

        return new_state, dt

    @property
    def is_stochastic(self) -> bool:
        return True
```

### Ensemble mode

Because a single SDE run is a random sample, the engine runs SDE-containing experiments in ensemble mode automatically when `solver.is_stochastic` returns True.

```yaml
# experiment config signals ensemble
scheduler:
  ensemble_size: 500    # run 500 trajectories in parallel
  t_end: 365.0
  summarize:
    - percentile: [5, 25, 50, 75, 95]   # emit percentile bands, not raw trajectories
    - metric: price
```

The orchestrator fans out `ensemble_size` independent runs (different seeds, same config), collects the metric distributions from each, and emits percentile bands to TimescaleDB rather than individual trajectories.

### Tuning parameters

| Parameter | Typical value | Effect |
|---|---|---|
| `dt` (fixed) | `1e-3` to `1e-1` | Smaller = more accurate but slower. Unlike ODE, there is no adaptive step size in standard SDE schemes. |
| `method` | `euler_maruyama` | Switch to `milstein` when noise is multiplicative and strong convergence matters. |
| `ensemble_size` | 100–1000 | More samples = tighter confidence intervals. 200 is usually sufficient for 5th/95th percentile estimation. |
| `seed` | Per-run | The engine generates `base_seed + run_index` for each ensemble member, ensuring reproducibility of the entire ensemble. |

---

## 13. Technology Stack

### Engine (Python — Phase 1, Rust — Phase 3)

| Component | Technology | Rationale |
|---|---|---|
| ODE integration | `scipy.integrate.solve_ivp` | Production-grade adaptive solvers (RK45, Radau, BDF) |
| SDE integration | `numpy` (Euler-Maruyama / Milstein) | No scipy equivalent; implemented directly |
| PDE grid ops | `numpy` + optional `cupy` | NumPy for CPU, CuPy for GPU (same API) |
| ABM agent loop | `numba` JIT + `numpy` | JIT-compiled parallelism without leaving Python |
| Spatial indexing | `scipy.spatial.cKDTree` or custom grid hash | O(log N) or O(1) neighbor queries |
| Graph propagation | `scipy.sparse` for large, plain dicts for small | Vectorized adjacency operations |
| Parallelism | `concurrent.futures` (CPU), `cupy` (GPU) | Phase 1: threads; Phase 3: MPI via `mpi4py` |
| Rust core (Phase 3) | `ndarray`, `rayon`, `pyo3` | Zero-cost parallelism; Python bindings via pyo3 |

### API layer

| Component | Technology | Rationale |
|---|---|---|
| REST + WebSocket API | Hono.js (TypeScript) | Lightweight, edge-native, excellent WebSocket support |
| Runtime | Bun | Fast startup, native TypeScript, compatible with Hono |
| Auth | JWT + API keys | Stateless; AI agents use API keys, humans use JWT |
| Real-time streaming | Server-Sent Events (SSE) via Hono | Push metric updates to UI without polling |

### Frontend

| Component | Technology | Rationale |
|---|---|---|
| UI framework | Svelte 5 + SvelteKit | Minimal runtime, reactive, excellent for real-time data |
| Visualization | D3.js + Canvas API | D3 for charts/graphs, Canvas for large grid rendering |
| Real-time updates | SSE client | Receives metric stream from Hono API |
| State management | Svelte stores | Native to Svelte; no Redux overhead |
| Styling | Tailwind CSS | Utility-first, consistent design system |

### Storage

| Component | Technology | Rationale |
|---|---|---|
| Time-series metrics | TimescaleDB (PostgreSQL extension) | SQL-compatible, excellent for dense metric streams, hypertable compression |
| Event log / analytics | ClickHouse | Columnar, extremely fast for aggregation queries over billions of events |
| Data bus (runtime) | Redis | Sub-millisecond pub/sub; TTL-based channel expiry |
| Artefact storage | Local filesystem (Phase 1), S3-compatible (Phase 3) | Run snapshots, checkpoints, exported results |
| Run metadata | PostgreSQL | Experiments, configs, run history, user management |

### Infrastructure

| Component | Technology |
|---|---|
| Containerization | Docker + Docker Compose (dev), Kubernetes (prod) |
| Python package | `uv` for dependency management |
| JS package | Bun |
| CLI | Python (`typer`) |
| Config format | YAML (experiment configs), TOML (engine config) |
| Observability | OpenTelemetry → Grafana |

---

## 14. Project File Structure

Long term, plugins are not maintained inside the core engine repository. The engine repo contains only the core, solvers, storage, and infrastructure; production plugins live in their own repos and are installed via pip.

For Version 1 development, this repo may temporarily behave as a monorepo with `sdk/` and `plugins/persephone-plugin-sir-epidemic/` checked in locally. Those packages are still installed and discovered through normal Python packaging entry points, so the core engine never directly imports plugin modules.

```
# ── Persephone core engine repo ──────────────────────────────────────────────
persephone/
│
├── README.md
├── Persephone.md                        ← this document
├── docker-compose.yml
├── pyproject.toml                     ← depends on persephone-sdk; no plugin imports
├── package.json                       ← Bun workspace root
│
├── engine/                            ← Python simulation engine
│   ├── __init__.py
│   ├── pyproject.toml
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py                  ← SimEngine: main orchestrator
│   │   ├── scheduler.py               ← Multi-rate scheduler
│   │   ├── bus.py                     ← DataBus (memory + Redis backends)
│   │   ├── run.py                     ← RunContext: one simulation run
│   │   ├── registry.py                ← Plugin discovery via entry_points()
│   │   └── types.py                   ← Shared type aliases
│   │
│   ├── solvers/
│   │   ├── __init__.py
│   │   ├── ode.py                     ← ODESolverWrapper (scipy RK45/Radau)
│   │   ├── pde.py                     ← PDESolverWrapper (finite difference)
│   │   ├── abm.py                     ← ABMSolverWrapper (agent loop + spatial hash)
│   │   ├── graph.py                   ← GraphSolverWrapper (propagation)
│   │   └── sde.py                     ← SDESolverWrapper (Euler-Maruyama / Milstein)
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── timescale.py               ← TimescaleDB writer
│   │   ├── clickhouse.py              ← ClickHouse event log writer
│   │   └── artefact.py                ← Checkpoint + snapshot IO
│   │
│   ├── compute/
│   │   ├── __init__.py
│   │   ├── threadpool.py              ← CPU parallel dispatch
│   │   ├── gpu.py                     ← CuPy / CUDA utilities
│   │   └── mpi.py                     ← MPI harness (Phase 3)
│   │
│   └── tests/
│       ├── test_ode.py
│       ├── test_pde.py
│       ├── test_abm.py
│       ├── test_graph.py
│       ├── test_sde.py
│       ├── test_bus.py
│       ├── test_scheduler.py
│       └── test_registry.py           ← tests that entry_point discovery works
│
├── engine-rs/                         ← Rust engine core (Phase 3)
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs                     ← pyo3 Python bindings
│   │   ├── solver/
│   │   │   ├── mod.rs
│   │   │   ├── ode.rs
│   │   │   ├── pde.rs
│   │   │   ├── abm.rs
│   │   │   └── sde.rs
│   │   ├── bus.rs
│   │   └── scheduler.rs
│   └── tests/
│       └── integration.rs
│
├── api/                               ← Hono.js API server
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts
│   │   ├── routes/
│   │   │   ├── runs.ts
│   │   │   ├── experiments.ts
│   │   │   ├── metrics.ts
│   │   │   ├── plugins.ts             ← GET /plugins proxies registry.list_all()
│   │   │   └── auth.ts
│   │   ├── middleware/
│   │   │   ├── auth.ts
│   │   │   └── logger.ts
│   │   ├── engine-client.ts
│   │   └── types.ts
│   └── tests/
│       └── routes.test.ts
│
├── ui/                                ← Svelte 5 + SvelteKit frontend
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.ts
│   ├── src/
│   │   ├── app.html
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── stores/
│   │   │   │   ├── run.ts
│   │   │   │   ├── metrics.ts
│   │   │   │   └── experiment.ts
│   │   │   ├── components/
│   │   │   │   ├── RunPanel.svelte
│   │   │   │   ├── MetricChart.svelte
│   │   │   │   ├── FieldViewer.svelte
│   │   │   │   ├── AgentViewer.svelte
│   │   │   │   ├── GraphViewer.svelte
│   │   │   │   └── PluginBrowser.svelte
│   │   │   └── viz/
│   │   │       ├── colormap.ts
│   │   │       └── canvas.ts
│   │   └── routes/
│   │       ├── +layout.svelte
│   │       ├── +page.svelte
│   │       ├── experiments/[id]/+page.svelte
│   │       └── runs/[id]/+page.svelte
│   └── tests/
│       └── components.test.ts
│
├── cli/                               ← Python CLI (typer)
│   ├── __init__.py
│   ├── main.py
│   └── commands/
│       ├── run.py                     ← persephone run <config.yaml>
│       ├── sweep.py                   ← persephone sweep <sweep.yaml>
│       ├── replay.py                  ← persephone replay <run_id>
│       ├── plugins.py                 ← persephone plugins list | install <name>
│       └── export.py                  ← persephone export <run_id> --format parquet
│
├── configs/
│   ├── engine.toml
│   └── examples/
│       ├── sir_epidemic.yaml
│       ├── heat_diffusion.yaml
│       └── city_epidemic.yaml
│
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile.engine
│   ├── Dockerfile.api
│   ├── Dockerfile.ui
│   └── k8s/
│
└── docs/
    ├── plugin-sdk.md
    ├── api-reference.md
    └── math-reference.md


# ── persephone-sdk repo (separate, published to PyPI) ──────────────────────────
persephone-sdk/
├── persephone_sdk/
│   ├── __init__.py
│   ├── plugin.py                      ← PluginManifest + World/Solver/Observer/Renderer ABCs
│   ├── testing.py                     ← PluginTestHarness
│   └── validators.py                  ← bus schema + shape + unit validators
├── pyproject.toml
└── README.md


# ── Example first-party plugin repo (template for community plugins) ─────────
persephone-plugin-sir-epidemic/
├── persephone_sir_epidemic/
│   ├── __init__.py                    ← exports SIREpidemicPlugin with static manifest()
│   ├── world.py
│   ├── solver.py
│   ├── observer.py
│   └── renderer.py
├── tests/
│   └── test_compliance.py             ← runs PluginTestHarness
├── pyproject.toml                     ← declares entry point "persephone.plugins"
└── README.md
```

---

## 15. Data Schemas

### Experiment config (YAML)

```yaml
# configs/examples/city_epidemic.yaml
name: city_epidemic_baseline
description: "Four-paradigm city epidemic simulation"
seed: 42

solvers:
  - type: ode
    plugin: biology.viral_ode
    params:
      mutation_rate: 0.01
      initial_viral_load: 1000.0

  - type: pde
    plugin: biology.aerosol_pde
    params:
      diffusion_coeff: 0.5
      decay_rate: 0.02
      grid_size: [256, 256]
      dx: 1.0   # metres per cell

  - type: abm
    plugin: biology.human_behavior
    params:
      n_agents: 10000
      mask_compliance: 0.6
      isolation_threshold: 0.3

  - type: graph
    plugin: biology.sir_epidemic
    params:
      p_infect: 0.15
      p_recover: 0.05
      network_type: small_world
      n_nodes: 10000
      k: 6
      rewire_p: 0.1

coupling:
  rules:
    infection_map: sum
    viral_fitness: max
    aerosol_grid: last
    agent_states: last

scheduler:
  sync_interval: auto   # uses min(preferred_dt) across all active solvers
  t_end: 365.0          # 1 year

observer:
  metrics:
    - infected_count
    - susceptible_count
    - recovered_count
    - peak_aerosol
    - viral_fitness
  emit_every: 1.0       # emit metrics every 1 time unit

storage:
  timescale: true
  clickhouse: true
  checkpoint_every: 50  # save state every 50 time units
```

### TimescaleDB schema

```sql
-- One row per metric per time step per run
CREATE TABLE metrics (
    run_id      UUID         NOT NULL,
    t           DOUBLE PRECISION NOT NULL,
    metric      TEXT         NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    solver_id   TEXT,
    tags        JSONB,
    PRIMARY KEY (run_id, t, metric)
);

SELECT create_hypertable('metrics', 't', chunk_time_interval => 10.0);
CREATE INDEX ON metrics (run_id, metric, t DESC);
```

### ClickHouse schema

```sql
-- Append-only event log: discrete events (agent state changes, threshold crossings)
CREATE TABLE events (
    run_id      String,
    t           Float64,
    event_type  String,
    entity_id   UInt64,
    old_state   String,
    new_state   String,
    payload     String    -- JSON
) ENGINE = MergeTree()
  PARTITION BY toYYYYMM(toDateTime(t))
  ORDER BY (run_id, t, event_type);
```

### PostgreSQL schema (run metadata)

```sql
CREATE TABLE experiments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    config      JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    created_by  TEXT
);

CREATE TABLE runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id   UUID REFERENCES experiments(id),
    seed            BIGINT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    -- status: pending | running | completed | failed | cancelled
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    t_current       DOUBLE PRECISION DEFAULT 0,
    t_end           DOUBLE PRECISION,
    config_snapshot JSONB,          -- exact config used (immutable after start)
    error_message   TEXT
);
```

---

## 16. API Design

All endpoints are prefixed `/api/v1`.

### Runs

```
POST   /api/v1/runs                    Start a new run from a config
GET    /api/v1/runs/:id                Get run status and metadata
DELETE /api/v1/runs/:id                Cancel a running simulation
GET    /api/v1/runs/:id/metrics        SSE stream of live metrics
GET    /api/v1/runs/:id/state          Current world state snapshot
GET    /api/v1/runs/:id/checkpoint/:t  State snapshot at time t
```

### Experiments

```
POST   /api/v1/experiments             Create experiment
GET    /api/v1/experiments             List experiments (paginated)
GET    /api/v1/experiments/:id         Get experiment + all run summaries
POST   /api/v1/experiments/:id/sweep   Launch a parameter sweep
```

### Plugins

```
GET    /api/v1/plugins                 List installed plugins
GET    /api/v1/plugins/:id             Plugin metadata + param schema
POST   /api/v1/plugins                 Install a plugin (admin only)
```

### SSE metric stream format

```typescript
// Each SSE event is a JSON object:
type MetricEvent = {
  run_id: string;
  t: number;
  metrics: Record<string, number>;  // { infected_count: 1240, viral_fitness: 0.87, ... }
  tick: number;
};
```

### Hono.js route skeleton

```typescript
// api/src/routes/runs.ts
import { Hono } from 'hono'
import { streamSSE } from 'hono/streaming'
import { authMiddleware } from '../middleware/auth'
import { engineClient } from '../engine-client'

const runs = new Hono()

runs.use('*', authMiddleware)

runs.post('/', async (c) => {
  const config = await c.req.json()
  const run = await engineClient.startRun(config)
  return c.json(run, 201)
})

runs.get('/:id', async (c) => {
  const run = await engineClient.getRun(c.req.param('id'))
  if (!run) return c.notFound()
  return c.json(run)
})

runs.get('/:id/metrics', (c) => {
  const runId = c.req.param('id')
  return streamSSE(c, async (stream) => {
    for await (const event of engineClient.streamMetrics(runId)) {
      await stream.writeSSE({
        data: JSON.stringify(event),
        event: 'metric',
      })
    }
  })
})

export { runs }
```

---

## 17. Build & Run

### Prerequisites

- Python 3.11+
- Bun 1.1+
- Docker + Docker Compose
- (Optional) CUDA 12+ for GPU acceleration
- (Optional) Rust 1.78+ for Phase 3 engine

### Development setup

```bash
# 1. Clone and enter the project
git clone https://github.com/your-org/persephone
cd persephone

# 2. Start infrastructure (Redis, TimescaleDB, ClickHouse, Postgres)
docker compose up -d redis timescale clickhouse postgres

# 3. Install Python dependencies
pip install uv
uv sync

# 4. Install JS dependencies
bun install

# 5. Initialize databases
uv run python -m engine.storage.timescale --init
uv run python -m engine.storage.clickhouse --init

# 6. Start the API server (dev mode, hot reload)
cd api && bun dev

# 7. Start the UI (dev mode, hot reload)
cd ui && bun dev

# 8. Run a test simulation
uv run persephone run configs/examples/sir_epidemic.yaml
```

### Running a simulation from CLI

```bash
# Single run
persephone run configs/examples/city_epidemic.yaml

# Parameter sweep (runs in parallel)
persephone sweep configs/examples/sweep_infection_rate.yaml --workers 8

# Replay a completed run
persephone replay <run_id> --speed 10x

# Export results
persephone export <run_id> --format parquet --output ./results/
```

### Docker Compose (full stack)

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: persephone
      POSTGRES_USER: persephone
      POSTGRES_PASSWORD: persephone
    ports: ["5432:5432"]

  clickhouse:
    image: clickhouse/clickhouse-server:24
    ports: ["8123:8123", "9000:9000"]
    volumes:
      - ./infra/clickhouse-config:/etc/clickhouse-server/config.d

  api:
    build:
      context: ./api
      dockerfile: ../infra/Dockerfile.api
    ports: ["3000:3000"]
    environment:
      DATABASE_URL: postgres://persephone:persephone@postgres:5432/persephone
      REDIS_URL: redis://redis:6379
    depends_on: [postgres, redis]

  ui:
    build:
      context: ./ui
      dockerfile: ../infra/Dockerfile.ui
    ports: ["5173:5173"]
    environment:
      PUBLIC_API_URL: http://localhost:3000

  engine:
    build:
      context: .
      dockerfile: ./infra/Dockerfile.engine
    environment:
      DATABASE_URL: postgres://persephone:persephone@postgres:5432/persephone
      REDIS_URL: redis://redis:6379
      CLICKHOUSE_URL: http://clickhouse:8123
    depends_on: [postgres, redis, clickhouse]
    volumes:
      - ./engine:/app/engine
      - ./configs:/app/configs
```

---

## 18. Phase Roadmap

### Phase 1 — Working kernel (months 1–3)
**Goal:** A simulation runs end-to-end. Data is stored. The CLI works.

- [ ] `World`, `Solver`, `Observer`, `Renderer` ABC definitions (in `persephone-sdk`)
- [ ] ODE solver wrapper (scipy RK45)
- [ ] PDE solver wrapper (numpy finite difference)
- [ ] ABM solver wrapper (Python agent loop, basic spatial hash)
- [ ] Graph solver wrapper (adjacency list, SIR propagation)
- [ ] SDE solver wrapper (Euler-Maruyama, fixed dt)
- [ ] In-memory DataBus (Python dict)
- [ ] Multi-rate scheduler (basic, fixed sync interval)
- [ ] Plugin discovery via `importlib.metadata.entry_points()`
- [ ] `persephone-plugin-sir-epidemic` (Graph) — first external plugin
- [ ] `persephone-plugin-heat-diffusion` (PDE)
- [ ] `persephone-plugin-viral-ode` (ODE)
- [ ] TimescaleDB writer (Observer)
- [ ] CLI: `persephone run <config.yaml>` and `persephone plugins list`
- [ ] Tests for each solver + `PluginTestHarness` in SDK

### Phase 2 — Research-grade correctness (months 3–5)
**Goal:** Results are scientifically trustworthy. A real researcher can use this.

- [ ] Adaptive step size (RK45 tolerances exposed in config)
- [ ] Stiff system detection + Radau/BDF fallback
- [ ] Milstein scheme for SDE (plugin declares `diffusion_derivative()`)
- [ ] SDE ensemble mode (fan-out N runs, emit percentile bands)
- [ ] CFL enforcement in PDE solver
- [ ] `numba` JIT for ABM inner loop
- [ ] Redis DataBus backend
- [ ] Static bus channel validation (pre-run check for missing channels)
- [ ] Parameter sweep orchestrator
- [ ] Run versioning + reproducibility (config + seed → identical results)
- [ ] ClickHouse event log
- [ ] Hono.js API (runs, experiments, metrics SSE)
- [ ] Svelte UI: run panel, metric charts, field viewer

### Phase 3 — Scale and AI interface (months 5–10)
**Goal:** Runs at HPC scale. AI agents can drive simulations programmatically.

- [ ] Rust engine core (pyo3 bindings for ODE, PDE, ABM, SDE inner loops)
- [ ] GPU acceleration (CuPy PDE, CUDA kernels for large grids)
- [ ] MPI parameter sweep distribution
- [ ] Plugin SDK hardened + WASM sandbox for community plugins
- [ ] Python SDK for AI agents (`persephone.run()`, `persephone.observe()`, `persephone.steer()`)
- [ ] Dense output for ODE (query state at any t without re-running)
- [ ] Checkpoint + resume
- [ ] S3-compatible artefact storage
- [ ] Kubernetes deployment manifests
- [ ] Experiment diff tool (compare two run results)

### Phase 4 — Ecosystem (months 10–14)
**Goal:** Others can build on Persephone.

- [ ] Plugin registry at `plugins.persephone.io` (publish, install, version community plugins)
- [ ] `persephone plugins install <name>` resolves from registry + pip installs
- [ ] Notebook integration (Jupyter widget)
- [ ] `persephone.ai` API key system
- [ ] Plugin SDK documentation + tutorial
- [ ] GUI plugin builder (no-code world definition)
- [ ] Multi-simulation coupling (two independent experiments sharing a bus channel)

---

## 19. Simulation Domains & Data Sources

Each domain below specifies: what paradigms it exercises, what data the simulation actually needs (in plain language), where to get that data, how to transform it into Persephone's state format, and which plugin it corresponds to.

---

### Data Requirements — Plain Language Standard

Every domain entry uses this format for data requirements:

**What the simulation needs (plain language):** A description of the real-world quantities required, written so a domain expert who has never used Persephone can understand and collect them.

**Minimum viable data:** The smallest dataset that makes the simulation runnable and scientifically non-trivial.

**What to collect if you want accuracy:** Additional data that improves realism but is not required for the simulation to run.

The transformation code shows how to go from the raw collected data to the numpy arrays the plugin's `World.init()` expects.

---

### Domain 1: LLM Inference Cluster — Latency & Throughput Under Load

**Paradigms:** Graph (request routing) + ODE (queue depth dynamics) + SDE (request arrival noise)

**What the simulation needs (plain language):**
- The topology of your inference cluster: which servers exist, how many GPUs each has, how they connect to a load balancer
- Request arrival patterns: how many requests per second arrive, and how bursty that arrival is
- Per-request resource profile: how long a request takes to process on one GPU, and how that scales with token length
- Failure rates: how often individual GPUs or servers go offline

**Minimum viable data:** A list of server nodes with GPU count, a mean requests/second, a mean time-per-request in seconds, and a coefficient of variation for burstiness. This can come entirely from internal documentation or estimates — no instrumentation needed to start.

**What to collect if you want accuracy:** Actual request logs with timestamps, token counts, and per-request latency; GPU utilization time series from `nvidia-smi`; load balancer access logs.

**Data sources:**
- OpenLLM Benchmark results (`https://github.com/bentoml/openllm-benchmark`) — throughput and latency tables for common model/hardware combinations. CSV download, no API.
- MLCommons Inference results (`https://mlcommons.org/benchmarks/inference-datacenter/`) — standardized latency/throughput curves across hardware.
- Your own cluster: `prometheus` + `nvidia_gpu_exporter` → query via PromQL API.

**Transformation:**

```python
import pandas as pd, numpy as np

# From MLCommons or your own Prometheus export:
# df columns: server_id, gpu_count, mean_latency_ms, p99_latency_ms, throughput_rps
df = pd.read_csv('cluster_benchmarks.csv')

# Graph: nodes = servers, edges = load balancer connections
nodes = {row.server_id: {'gpu_count': row.gpu_count, 'state': 'idle'}
         for _, row in df.iterrows()}
edges = [('load_balancer', sid, 1.0) for sid in df.server_id]

# ODE: queue depth per server — initial state is empty queues
queue_depth_init = np.zeros(len(df))

# SDE: request arrival — Poisson rate + noise
mean_rps   = df['throughput_rps'].mean()
noise_coef = 0.3   # 30% coefficient of variation, tune from logs

world_state = {
    'queue_depths':    queue_depth_init,
    'server_states':   np.array([0]*len(df)),     # 0=idle, 1=busy, 2=failed
    'arrival_rate':    np.array([mean_rps]),
    'mean_latency_ms': df['mean_latency_ms'].values,
}
```

**What to measure:** Queue depth distribution over time, P99 latency under load, server utilization, time-to-saturation as load ramps. Sweep `arrival_rate` to find the saturation point.

---

### Domain 2: CI/CD Pipeline Congestion

**Paradigms:** Graph (pipeline dependency DAG) + ABM (individual build jobs as agents) + ODE (resource pool dynamics)

**What the simulation needs (plain language):**
- The dependency structure of your build pipeline: which jobs must complete before others can start, and how long each job typically takes
- The resource pool: how many parallel runners exist and how jobs compete for them
- Historical job duration distributions: not just the mean, but the variance — flaky jobs occasionally take 10x longer

**Minimum viable data:** A pipeline YAML (GitHub Actions, GitLab CI, or Jenkins), a list of jobs with mean and standard deviation of duration, and the number of available runners.

**What to collect if you want accuracy:** Full job duration history from your CI provider's API; queue wait times; runner utilization by time of day.

**Data sources:**
- GitHub Actions API: `GET /repos/{owner}/{repo}/actions/runs` with job timing data. Requires a personal access token.
- GitLab CI API: `GET /projects/:id/jobs` returns duration, queued_duration, status for every job.
- `pip install google-cloud-build` for Cloud Build history.

**Transformation:**

```python
import requests, numpy as np, yaml
from collections import defaultdict

# GitHub Actions: fetch last N workflow runs and compute per-job duration stats
headers = {'Authorization': 'token YOUR_PAT'}
runs = requests.get(
    'https://api.github.com/repos/ORG/REPO/actions/runs?per_page=100',
    headers=headers
).json()['workflow_runs']

job_stats = defaultdict(list)
for run in runs[:200]:
    jobs = requests.get(run['jobs_url'], headers=headers).json()['jobs']
    for job in jobs:
        duration = (pd.Timestamp(job['completed_at']) -
                    pd.Timestamp(job['started_at'])).seconds
        job_stats[job['name']].append(duration)

job_params = {name: {'mean_s': np.mean(d), 'std_s': np.std(d)}
              for name, d in job_stats.items()}

# Graph: adjacency from pipeline YAML 'needs:' declarations
pipeline = yaml.safe_load(open('.github/workflows/ci.yml'))
edges = []
for job_name, job_def in pipeline['jobs'].items():
    for dep in job_def.get('needs', []):
        edges.append((dep, job_name, 1.0))

n_runners = 8   # from your CI config
```

**What to measure:** Mean queue wait time vs. number of runners (sweep `n_runners`), probability that a full pipeline exceeds a time budget, effect of one flaky job on downstream queue depth.

---

### Domain 3: Microservice Failure Cascade

**Paradigms:** Graph (service dependency topology) + ODE (error rate dynamics per service) + ABM (individual requests as traceable agents)

**What the simulation needs (plain language):**
- A map of which services call which other services, and with what frequency
- For each service: its normal error rate, its latency distribution, and its timeout/retry behavior
- Circuit breaker configuration: at what error rate does a service stop sending traffic to a dependency?
- Traffic volume: requests per second at the entry points

**Minimum viable data:** A service dependency graph (extracted from a service mesh or drawn manually), traffic volume at the entry point, and timeout/retry configs.

**What to collect if you want accuracy:** Distributed traces (Jaeger, Zipkin, or AWS X-Ray) giving real per-edge latency distributions and real error rates.

**Data sources:**
- Jaeger API: `GET /api/dependencies` gives the service graph with call counts directly.
- AWS X-Ray: `get_service_graph` API call returns a JSON service map with edge call counts and error rates.
- Istio/Prometheus: `istio_requests_total` metric with `response_code` label gives per-edge error rates.

**Transformation:**

```python
import requests, numpy as np

deps = requests.get('http://localhost:16686/api/dependencies').json()['data']
# deps: list of {parent: str, child: str, callCount: int}

nodes = list({d['parent'] for d in deps} | {d['child'] for d in deps})
node_idx = {n: i for i, n in enumerate(nodes)}
n = len(nodes)

call_matrix  = np.zeros((n, n))
total_calls  = sum(d['callCount'] for d in deps)
for d in deps:
    i, j = node_idx[d['parent']], node_idx[d['child']]
    call_matrix[i, j] = d['callCount'] / total_calls

# ODE: per-service error rate — inject failure at t=0 to watch cascade
error_rates = np.array([0.001] * n)
error_rates[node_idx['payment-service']] = 1.0

world_state = {
    'error_rates':    error_rates,
    'call_matrix':    call_matrix,
    'service_states': np.zeros(n),    # 0=healthy, 1=degraded, 2=circuit-open
}
```

**What to measure:** Time-to-cascade, number of services affected vs. initial blast radius, recovery time after root cause is resolved. Counterfactual: what if the circuit breaker threshold were 10% vs. 50%?

---

### Domain 4: Organizational Knowledge Diffusion

**Paradigms:** Graph (org chart / collaboration network) + ABM (individual employees) + SDE (learning noise)

**What the simulation needs (plain language):**
- The structure of the organization: who reports to whom, and who collaborates informally
- A representation of knowledge or expertise — a scalar skill level per domain per employee is sufficient
- How knowledge spreads: through meetings, documentation, pair programming, or informal conversation — and the probability that any given interaction transfers knowledge
- Attrition rate: how often employees leave, taking knowledge with them

**Minimum viable data:** An org chart (hierarchy), team sizes, and an estimate of cross-team interaction frequency. Knowledge transfer rate can be a parameter you sweep.

**What to collect if you want accuracy:** Collaboration data from GitHub (who reviews whose PRs), Slack analytics (who messages whom — no content needed), or meeting calendars. These give the informal collaboration graph which matters more than the org chart.

**Data sources:**
- GitHub API: `GET /repos/{owner}/{repo}/pulls?state=closed` → `requested_reviewers` and `review_comments` build a reviewer graph.
- Slack Analytics (Enterprise Grid): workspace analytics export gives message counts between channels/users (no message content).
- Linear/Jira: who comments on whose issues — proxy for collaboration intensity.

**Transformation:**

```python
import requests, numpy as np
from collections import defaultdict

headers = {'Authorization': 'token YOUR_PAT'}
prs = requests.get(
    'https://api.github.com/repos/ORG/REPO/pulls?state=closed&per_page=100',
    headers=headers
).json()

collab_counts = defaultdict(int)
for pr in prs:
    author = pr['user']['login']
    reviews = requests.get(pr['url'] + '/reviews', headers=headers).json()
    for review in reviews:
        reviewer = review['user']['login']
        if reviewer != author:
            collab_counts[(author, reviewer)] += 1
            collab_counts[(reviewer, author)] += 1

max_count = max(collab_counts.values())
edges = [(u, v, count / max_count) for (u, v), count in collab_counts.items()]

# ABM: each employee has a knowledge vector across domains
all_users = list({u for u, v, _ in edges} | {v for u, v, _ in edges})
n_employees = len(all_users)
n_domains = 5   # e.g. [frontend, backend, infra, ml, data]
knowledge = np.random.beta(2, 5, size=(n_employees, n_domains))

world_state = {
    'knowledge':      knowledge,
    'collab_graph':   np.array(edges),
    'attrition_rate': np.array([0.02]),   # 2% monthly
    'noise_scale':    np.array([0.05]),   # SDE: how unpredictable is any given interaction
}
```

**What to measure:** Knowledge entropy across the organization over time, bus-factor (how many employees hold >50% of knowledge in a domain), time to re-learn after attrition, effect of onboarding rate on knowledge distribution.

---

### Domain 5: Reinforcement Learning Training Dynamics

**Paradigms:** ODE (policy gradient dynamics in parameter space) + SDE (stochastic gradient noise)

**What the simulation needs (plain language):**
- The learning rate schedule and optimizer hyperparameters from your training config
- A measure of loss landscape curvature — approximated from a few training runs as the ratio of gradient variance to gradient mean
- The relationship between batch size and gradient noise — larger batches = less noise
- For distributed training: gradient synchronization topology

**Minimum viable data:** A training log (loss vs. step), learning rate schedule, and batch size. Everything else can be estimated from the log.

**What to collect if you want accuracy:** Gradient norm per step (log via `torch.nn.utils.clip_grad_norm_`), per-layer gradient statistics, distributed synchronization timing.

**Data sources:**
- Weights & Biases: `wandb.Api().runs(PROJECT)` returns full training history including all logged metrics as a DataFrame. `pip install wandb`.
- MLflow: `mlflow.search_runs(experiment_ids=[...])` returns the same.
- TensorBoard: `from tensorboard.backend.event_processing import event_accumulator`.

**Transformation:**

```python
import wandb, numpy as np
from scipy.signal import savgol_filter

api = wandb.Api()
run = api.run("myorg/myproject/RUN_ID")
history = run.history(keys=['train/loss', 'train/grad_norm', 'train/lr'])

loss      = history['train/loss'].values
grad_norm = history['train/grad_norm'].values
lr        = history['train/lr'].values

# Gradient noise scale B = variance / mean^2
# This is the SDE diffusion parameter: larger B = noisier training
grad_mean    = np.mean(grad_norm)
grad_var     = np.var(grad_norm)
noise_scale_B = grad_var / (grad_mean ** 2 + 1e-8)

world_state = {
    'loss':        np.array([loss[0]]),
    'lr':          np.array([lr[0]]),
    'noise_scale': np.array([noise_scale_B]),  # SDE diffusion parameter
    'step':        np.array([0.0]),
}
```

**What to measure:** Loss trajectory distribution under different learning rate schedules, probability of loss explosion vs. batch size, time-to-convergence as a function of noise scale. Useful for understanding *why* a training run failed — replay the dynamics under different hyperparameters without re-running actual training.

---

### Domain 6: Feature Flag Rollout Diffusion

**Paradigms:** Graph (user workspace/social graph) + ABM (individual users) + SDE (adoption noise)

**What the simulation needs (plain language):**
- A representation of the user population and how users are connected (through shared workspaces, teams, or social relationships)
- The rollout strategy: what percentage of users get the flag at each stage, and what the targeting criteria are
- Adoption dynamics: once a user has access to a feature, how quickly do they use it? Does seeing a teammate use it accelerate their own adoption?
- Churn risk: does showing a user an experimental feature increase churn risk if the feature has bugs?

**Minimum viable data:** User count, team/workspace structure (who is in the same workspace), rollout percentage schedule, and historical feature adoption curves from past rollouts.

**What to collect if you want accuracy:** A bipartite graph of users and workspaces (anonymized), daily active usage data per feature, churn events tied to feature exposure.

**Data sources:**
- LaunchDarkly API: `GET /api/v2/flags/{project}` gives flag configuration and targeting rules.
- Amplitude / Mixpanel: user event streams exported as CSV — filter to feature-specific events for adoption time series.
- Your own database: a `users` table + `workspace_members` table is sufficient to build the collaboration graph.

**Transformation:**

```python
import pandas as pd, numpy as np, networkx as nx

members = pd.read_csv('workspace_members.csv')  # columns: user_id, workspace_id

G = nx.Graph()
for workspace_id, group in members.groupby('workspace_id'):
    users = group['user_id'].tolist()
    for i in range(len(users)):
        for j in range(i+1, len(users)):
            if G.has_edge(users[i], users[j]):
                G[users[i]][users[j]]['weight'] += 1
            else:
                G.add_edge(users[i], users[j], weight=1)

max_w = max(d['weight'] for _, _, d in G.edges(data=True))
edges = np.array([[u, v, d['weight']/max_w]
                  for u, v, d in G.edges(data=True)])

n_users = G.number_of_nodes()
# ABM: user state — 0=no_access, 1=has_access_unused, 2=adopted, 3=churned
user_states = np.zeros(n_users, dtype=int)

world_state = {
    'user_states':    user_states,
    'collab_edges':   edges,
    'adoption_noise': np.array([0.15]),   # SDE: tune from historical rollout data
}
```

**What to measure:** Adoption rate over time vs. rollout percentage, social contagion multiplier (how much faster adoption spreads through connected workspaces), churn delta between exposed and unexposed cohorts, optimal rollout speed to maximize adoption while limiting churn risk.

---

## 20. Architecture Improvements & Fixes

This section tightens the original architecture into something that can be built without losing the larger vision. The system should remain powerful, but Version 1 must prove one complete vertical slice before adding distributed execution, GPU kernels, Rust acceleration, or a plugin marketplace.

---

### 20.1 Fix: define a strict Version 1 boundary

The earlier roadmap listed many correct long-term pieces, but it mixed kernel work, storage, API, UI, distributed compute, and ecosystem features in a way that could delay the first runnable system. Version 1 should be Python-first, local-first, deterministic, and plugin-driven:

- In scope for Version 1: `persephone-sdk`, Python engine core, in-memory bus, deterministic scheduler, one graph-based SIR plugin, one ready data source, CLI, run artefacts, and tests.
- Optional for Version 1 if time allows: minimal local API, Hono API, and Svelte UI.
- Out of scope for Version 1: Rust core, GPU acceleration, MPI, Kubernetes, community plugin marketplace, WASM sandbox, ClickHouse, and production auth.

This keeps the first release honest: a user can install the project, run a simulation from a config, inspect metrics, replay from artefacts, and install or develop at least one real plugin.

---

### 20.2 Fix: plugin packaging needs a local development path

The architecture correctly says production plugins should be external packages discovered through Python entry points. However, the first version also needs a smooth local development loop. Use both of these modes:

| Mode | Purpose | Mechanism |
|---|---|---|
| Installed plugin mode | Production and third-party usage | Python entry points under `persephone.plugins` |
| Editable workspace plugin mode | First-party development and examples | `uv pip install -e ./plugins/persephone-plugin-sir-epidemic` in the dev environment |

The core engine still must not import plugin modules directly. The editable plugin is installed as a package and discovered the same way as any external plugin.

---

### 20.3 Fix: the data bus should be double-buffered

The original data bus describes write-then-read ordering, but the example implementation stores only one current value per channel. That can accidentally let a solver read another solver's current-tick write depending on execution order. The Version 1 bus should be double-buffered:

- `read(channel)` always reads from the committed snapshot for tick `N`.
- `write(channel, value)` writes into a pending buffer for tick `N + 1`.
- `commit(tick)` atomically validates and promotes the pending buffer.
- Each record stores `run_id`, `tick`, `solver_id`, `schema_id`, `logical_time`, `value`, and optional `units`.

This makes scheduler behavior deterministic and prevents hidden ordering bugs.

---

### 20.4 Fix: formalize schemas before runtime

Every config, bus channel, metric, event, and plugin manifest should have a typed schema. For Version 1, use Pydantic models in Python and export JSON Schema for API/UI consumers later.

Required schemas:

- `ExperimentConfig`: run name, seed, scheduler, solvers, observers, storage, coupling rules.
- `SolverConfig`: paradigm, plugin entry point, version constraint, params.
- `PluginManifest`: metadata, paradigm, interfaces, bus reads/writes, parameter schema, metric schema.
- `BusChannelSchema`: channel name, dtype, shape, units, semantic version.
- `MetricRecord`: run id, solver id, metric name, value, logical time, tags.
- `RunManifest`: immutable provenance for a completed or failed run.

Schema validation should happen before any solver starts. A bad config should fail fast with a useful message.

---

### 20.5 Fix: reproducibility requires seeded substreams

One global seed is not enough for multi-solver or ensemble simulation. Version 1 should derive deterministic child random number generators from a base seed:

```python
seed_sequence = np.random.SeedSequence(base_seed)
solver_seeds = seed_sequence.spawn(len(active_solvers))
```

Each solver receives a named deterministic substream. Ensemble runs should use `base_seed + run_index` or spawned child sequences recorded in the run manifest. Reproducibility means:

- Same config bytes + same plugin versions + same seed + same engine version = same metrics.
- The run manifest records engine version, SDK version, plugin versions, config hash, Python version, platform, dependency lock hash, and seed plan.

---

### 20.6 Fix: observer and storage boundaries need stricter ownership

Observers should emit records; storage writers should persist them. The original description says the Observer writes to storage, but that couples plugin code to infrastructure. Better split:

- Plugin `Observer.observe(...)` returns metric/event records.
- Engine-owned `MetricSink` and `EventSink` persist those records.
- Version 1 sink writes JSONL and Parquet/CSV artefacts locally.
- Later sinks can write TimescaleDB and ClickHouse without changing plugins.

This keeps plugins portable and makes local runs possible without Docker.

---

### 20.7 Fix: `pickle` should not be the production wire format

The Redis bus example uses `pickle`, which is fine for throwaway local prototypes but unsafe for untrusted plugin ecosystems and brittle across versions. Version 1 can use in-memory NumPy arrays and local JSON/NPZ artefacts. Later Redis or network backends should use a safer binary representation such as Arrow IPC, MessagePack plus typed array payloads, or `.npy`/`.npz` blobs with schema metadata.

This is not optional polish. Deserializing untrusted pickle data is equivalent to arbitrary code execution. The moment community plugins can write to the Redis bus, any plugin can compromise the host process. Arrow IPC must be the default wire format for any networked backend, not a Phase 3 upgrade.

---

### 20.8 Fix: solver wrapper contracts should return elapsed time, not absolute time

The solver interface says `step()` returns `(new_state, actual_dt_advanced)`. Some examples return `self.t`, which is absolute solver time. The implementation should consistently return only the elapsed duration advanced during that call. The scheduler owns global logical time.

---

### 20.9 Fix: first plugin should be scientifically simple but complete

The best first plugin is `persephone-plugin-sir-epidemic`, a graph simulation of disease spread over a contact network. It is simple enough to validate, but rich enough to exercise the plugin SDK, graph solver, bus writes, observer metrics, config validation, seed reproducibility, data loading, and artefact output.

The first data source should be ready to run without API keys:

- `configs/examples/data/sir_contact_edges.csv`: a small contact network edge list.
- `configs/examples/sir_epidemic.yaml`: a runnable experiment config.
- Optional generator: `persephone examples generate-sir-network --nodes 500 --output configs/examples/data/sir_contact_edges.csv`.

This avoids making the first user depend on GitHub, Slack, Prometheus, or external credentials.

---

### 20.10 Fix: security and trust levels must be explicit

Version 1 should mark plugins as trusted Python code. Community sandboxing is a later feature. The docs and CLI should say this plainly:

- Installing a plugin executes Python code from that package.
- Only install trusted plugins in Version 1.
- Admin-only remote plugin installation belongs to a later production API.
- WASM sandboxing is Phase 3+ and should not be implied as already solved.

---

### 20.11 Fix: the ODE solver wrapper must not hardcode bus channel names

The `ODESolverWrapper` in section 8 hardcodes `bus.read('temperature_field')` and `bus.read('aerosol_grid')` directly in the engine's source code. This breaks the domain-agnostic promise: the engine now knows about biology. Every solver wrapper must read only the channels declared in the plugin manifest's `bus_reads` list, and write only to channels in `bus_writes`. The wrapper should never reference a domain-specific channel name.

```python
# Wrong — hardcoded domain knowledge in the engine
external = {
    'temperature': bus.read('temperature_field'),
    'aerosol':     bus.read('aerosol_grid'),
}

# Correct — driven entirely by the plugin manifest
external = {
    channel: bus.read(channel)
    for channel in self.plugin.manifest.bus_reads
}
```

This fix is required before any second plugin can be written. A domain-agnostic engine that reads `aerosol_grid` by name is not domain-agnostic.

---

### 20.12 Fix: the world state type contract must be extended beyond plain ndarray

The current contract uses `dict[str, np.ndarray]` as the universal state type. This is the right default, but it is insufficient for two common simulation patterns:

**Sparse graphs.** A dense adjacency matrix for a 100k-node social network requires 80GB of memory. The correct representation is a sparse matrix (`scipy.sparse.spmatrix`), but the current type contract rejects it. Forcing plugins to simulate sparsity inside a dense array is both wasteful and incorrect.

**Variable-size populations.** ABM agents that are born or die during simulation change the array shape each tick. The correct representation is a masked array (`np.ma.MaskedArray`) with a fixed maximum size and a boolean mask over active agents. The current contract has no mechanism for this.

The state type contract should be extended to:

```python
StateValue = np.ndarray | scipy.sparse.spmatrix | np.ma.MaskedArray
WorldState = dict[str, StateValue]
```

The `BusChannelSchema` should declare which type a channel carries. Solvers and the bus must handle all three without requiring plugins to work around the type system. Plain `np.ndarray` remains the default and is sufficient for most use cases; the extension is needed before graph-heavy or population-dynamic simulations are attempted.

---

### 20.13 Fix: coupling rules must support typed merge functions, not just string keywords

The current coupling rule system (`sum`, `mean`, `last`, `max`) works for scalar channels but silently produces wrong results for structured state. A plugin writing a 10k-node graph state to `infection_map` cannot be meaningfully `sum`-ed with another plugin's contribution — the keyword will either crash on shape mismatch or produce numerically nonsensical output.

Coupling rules should accept callable merge functions in addition to string keywords:

```python
# String keywords remain valid for scalar/vector channels
COUPLING_RULES = {
    'temperature':   'mean',
    'viral_fitness': 'max',
}

# Callable rules for structured state
def merge_infection_maps(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Union of two infection state arrays: infected beats susceptible."""
    return np.maximum(a, b)

COUPLING_RULES = {
    'infection_map': merge_infection_maps,
    'agent_states':  'last',
}
```

The experiment config should allow inline Python callables (for programmatic use) or named functions registered via the plugin SDK (for YAML configs). String keywords should be validated against a whitelist at config load time, not silently ignored at merge time.

---

### 20.14 Fix: operator splitting error must be documented and bounded

Operator splitting — advancing each solver independently for one `sync_interval` and then merging outputs — introduces a numerical splitting error proportional to `sync_interval`. This is well understood in the scientific computing literature but is currently undocumented in this architecture. For loosely-coupled paradigms (e.g. ODE viral dynamics and Graph infection propagation) the error is negligible at reasonable sync intervals. For tightly-coupled paradigms where the output of one solver is the input of another within the same tick (e.g. ABM behavior that reads a PDE aerosol field that the ABM itself modifies), artifacts can appear.

The following guidance should be added to the scheduler documentation:

- **Loose coupling** (paradigms that exchange state but do not depend on each other's sub-tick dynamics): `sync_interval` can be set to the slower solver's natural timestep. Splitting error is O(`sync_interval`).
- **Tight coupling** (paradigms that form a feedback loop within one tick): `sync_interval` should be set to the faster solver's `preferred_dt`. Consider Strang splitting (advance A for half a step, advance B for a full step, advance A for half a step) for second-order symmetric accuracy.
- The experiment config should expose a `splitting_order` option (`first_order` or `strang`) alongside `sync_interval`.

A warning should be emitted at config load time when `sync_interval` exceeds half the `preferred_dt` of any solver in a tight-coupling group.

---

### 20.15 Fix: the scheduler must support checkpoint and resume

Long-running simulations — multi-year climate models, large ensemble sweeps, parameter searches — will fail partway through due to hardware faults, memory exhaustion, or process interruption. The current artefact system mentions checkpoints but the scheduler has no concept of resuming from one. Without this, any interrupted long run must restart from tick 0.

The scheduler should support a first-class checkpoint/resume protocol:

- `checkpoint_every: N` in the experiment config triggers a full state snapshot every N ticks. This already appears in the config schema but is not wired to the scheduler.
- Each checkpoint saves: full `WorldState` dict (as `.npz`), bus committed snapshot, global logical time, RNG states for all active solvers, and the `RunManifest` up to that tick.
- The CLI should support `persephone replay --from-checkpoint <run_id>@<tick>` to resume from any saved checkpoint.
- Partial results up to the last checkpoint should always be queryable, even for failed runs.

This is not a Phase 3 feature. Any simulation long enough to be scientifically meaningful is long enough to be interrupted.

---

### 20.16 Fix: the scheduler must emit its own telemetry

When a simulation run is slow or produces unexpected results, the researcher currently has no visibility into the scheduler's internal behavior. There is no way to answer: which solver is consuming the most wall-clock time, how often is the CFL condition constraining the sync interval, or how frequently are coupling rules resolving conflicts. Debugging is guesswork.

The scheduler should emit structured telemetry alongside domain metrics:

```python
# Emitted once per sync interval to the MetricSink
SchedulerTelemetry(
    tick=int,
    logical_time=float,
    wall_time_ms=float,
    sync_interval_used=float,
    solver_step_times={solver_id: float},   # wall ms per solver
    cfl_constrained=bool,                   # True if PDE forced a smaller sync_interval
    coupling_conflicts={channel: int},      # number of multi-writer conflicts resolved
    bus_channel_sizes={channel: int},       # bytes per channel (detect unexpected growth)
)
```

This telemetry should be written to the same `MetricSink` as domain metrics, queryable via the same API, and visible in the Svelte UI alongside simulation output. Bottleneck identification and coupling debugging should require no code changes — just a query.

---

## 21. Glossary

| Term | Definition |
|---|---|
| **ABM** | Agent-Based Model. A simulation where individual agents follow local rules and collective behavior emerges. |
| **Adaptive step size** | A numerical integration technique where the solver chooses its own time step based on a local error estimate, growing it when safe and shrinking it when accuracy demands. |
| **Atol** | Absolute tolerance. The acceptable error when the state value is near zero. Companion to `rtol`. |
| **CFL condition** | Courant-Friedrichs-Lewy condition. A stability constraint on PDE solvers: the time step must be small enough that information does not "travel" more than one grid cell per step. |
| **Coupling rule** | A declarative rule that resolves conflicts when multiple solvers write to the same data bus channel in the same tick (e.g., `sum`, `mean`, `max`, `last`). |
| **Data bus** | A shared named key-value store through which solvers communicate without direct coupling. The only inter-solver communication mechanism in Persephone. |
| **Dense output** | An ODE solver feature that provides the solution as a continuous piecewise polynomial over the solved interval. Allows querying the solution at any intermediate time. |
| **Diffusion function g(x,t)** | The SDE component that scales the noise. If `g` depends on `x`, the noise is multiplicative (use Milstein); if constant, the noise is additive (Euler-Maruyama is sufficient). |
| **Drift function f(x,t)** | The deterministic ODE component of an SDE. Same role as `f` in `dx/dt = f(x,t)`. |
| **Ensemble** | A collection of SDE runs with different random seeds but identical parameters. The ensemble distribution — not any single run — is the simulation result. |
| **Entry point** | A Python packaging mechanism (`importlib.metadata.entry_points`) by which an installed package declares itself to another. Persephone uses the group `"persephone.plugins"` to discover all installed plugins at runtime without hardcoding. |
| **Euler-Maruyama** | The simplest SDE integrator: `x_next = x + f*dt + g*dW`. Strong order 0.5. Sufficient for most applications. |
| **Finite difference** | A method for approximating spatial derivatives on a grid by replacing them with differences between neighboring cell values. Used in the PDE solver. |
| **Graph simulation** | A simulation paradigm where entities are nodes and relationships are edges, and state transitions propagate along edges. |
| **Itô calculus** | The mathematical framework for SDEs used by Persephone. Noise is evaluated at the start of each step, not the midpoint. |
| **Laplacian (∇²)** | A differential operator measuring the average difference between a point and its neighbors. The core of heat diffusion, wave equations, and fluid simulations. |
| **Milstein** | An SDE integrator with strong order 1.0. Requires `dg/dx`. Preferred over Euler-Maruyama when noise is multiplicative. |
| **Multi-rate scheduler** | The engine component that manages solvers running at different time resolutions, advancing each at its own rate and synchronizing them at agreed intervals. |
| **Observer** | The plugin interface responsible for watching simulation state and emitting metrics to storage. The only interface that writes to the database. |
| **ODE** | Ordinary Differential Equation. A simulation paradigm where a small state vector evolves according to `dx/dt = f(x, t)`. |
| **Operator splitting** | A technique for advancing a multi-solver system: each solver is advanced independently for one synchronization interval, then outputs are merged. |
| **PDE** | Partial Differential Equation. A simulation paradigm where a spatial field evolves according to rules involving derivatives in both space and time. |
| **Plugin** | A self-contained Python package implementing the four-interface contract and registering itself via a `"persephone.plugins"` entry point. Lives outside the core engine repo, versioned independently. |
| **PluginManifest** | A dataclass (from `persephone-sdk`) that every plugin exposes via a static `manifest()` method. Contains metadata, class references, declared bus channels, and minimum SDK version. |
| **RK4** | Runge-Kutta 4th order. A fixed-step ODE integrator with O(dt⁴) error. |
| **RK45** | Runge-Kutta 4th/5th order adaptive. The standard production ODE solver. |
| **Rtol** | Relative tolerance. The acceptable error relative to the current state magnitude. |
| **Run** | One complete simulation execution: a specific experiment config + random seed. Fully reproducible. |
| **SDE** | Stochastic Differential Equation. A simulation paradigm where a state vector evolves under both a deterministic drift and a random noise term. Results are distributions, not single trajectories. |
| **persephone-sdk** | A separate Python package containing the four ABCs, `PluginManifest`, and `PluginTestHarness`. Both the engine and all plugins depend on it; plugins never depend on the engine directly. |
| **Solver** | The plugin interface responsible for advancing world state forward in time. |
| **Spatial hash** | A data structure that divides the world into a grid of cells and assigns agents to cells, enabling O(1) neighbor queries instead of O(N²). |
| **Stiff system** | An ODE system where components evolve at very different timescales, forcing explicit solvers to use tiny step sizes for stability. Requires implicit solvers (Radau, BDF). |
| **Strong convergence** | An SDE accuracy measure: how close is a single trajectory to the true path? Euler-Maruyama: order 0.5; Milstein: order 1.0. |
| **Sync interval** | The time window between data bus exchanges. Solvers run freely within their window; they exchange state only at sync boundaries. |
| **Weak convergence** | An SDE accuracy measure: how close are the statistical moments of the ensemble to the true distribution? Both Euler-Maruyama and Milstein achieve order 1.0. |
| **Wiener process (dW)** | The noise source in an SDE. Each increment is drawn from `N(0, dt)`. Independent across time steps. |
| **World** | The plugin interface responsible for defining the state schema and providing initialization and reset. |

---

*Persephone — build anything that changes over time.*
