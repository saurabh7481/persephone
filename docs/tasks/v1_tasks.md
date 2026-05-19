## 1. Version 1 Product Slice

### 1.1 Version 1 goal

Build a complete local simulation platform that can run one external plugin end-to-end:

> Given a YAML config and a contact-network CSV, Persephone discovers the SIR epidemic plugin, validates the config, runs a deterministic graph simulation, emits metrics, saves a run manifest and artefacts, and lets the user inspect or replay the result from the CLI.

### 1.2 Version 1 acceptance criteria

- [ ] A clean checkout can run `uv sync` and install the editable SIR plugin.
- [ ] `persephone plugins list` shows `sir_epidemic`.
- [ ] `persephone validate configs/examples/sir_epidemic.yaml` catches invalid config, missing data files, and incompatible plugin versions.
- [ ] `persephone run configs/examples/sir_epidemic.yaml` completes without external services.
- [ ] The run creates `runs/<run_id>/manifest.json`, `metrics.jsonl`, `events.jsonl`, and final state artefacts.
- [ ] Re-running the same config with the same seed produces byte-identical metrics or numerically identical metric records.
- [ ] Changing the seed changes stochastic infection outcomes.
- [ ] The PluginTestHarness passes against `persephone-plugin-sir-epidemic`.
- [ ] Unit tests cover the SDK interfaces, registry, config validation, bus, scheduler, graph solver, artefact store, CLI, and SIR plugin.
- [ ] The README explains setup, plugin installation, first run, and expected output.

### 1.3 Version 1 repository shape

The first implementation can use a monorepo for development while preserving package boundaries:

```text
persephone/
├── README.md
├── Persephone.md
├── pyproject.toml
├── uv.lock
├── src/
│   └── persephone/
│       ├── __init__.py
│       ├── cli/
│       ├── config/
│       ├── core/
│       ├── registry/
│       ├── solvers/
│       ├── storage/
│       └── examples/
├── sdk/
│   ├── pyproject.toml
│   └── src/persephone_sdk/
├── plugins/
│   └── persephone-plugin-sir-epidemic/
│       ├── pyproject.toml
│       ├── src/persephone_sir_epidemic/
│       └── tests/
├── configs/
│   └── examples/
│       ├── sir_epidemic.yaml
│       └── data/sir_contact_edges.csv
├── runs/
│   └── .gitkeep
├── docs/
└── tests/
```

The package boundaries still match the long-term architecture:

- `src/persephone`: engine and CLI.
- `sdk/src/persephone_sdk`: plugin contract package.
- `plugins/persephone-plugin-sir-epidemic`: first plugin package, installed editable during development.

### 1.4 First simulation plugin: SIR epidemic on a contact graph

**Plugin package:** `persephone-plugin-sir-epidemic`

**Entry point:** `sir_epidemic = "persephone_sir_epidemic:SIREpidemicPlugin"`

**Paradigm:** Graph

**Data source:** `configs/examples/data/sir_contact_edges.csv`

**CSV schema:**

```csv
source,target,weight
0,1,1.0
1,2,0.8
2,3,1.0
```

**Minimum parameters:**

```yaml
plugin: sir_epidemic
version: ">=0.1.0"
params:
  contact_graph: configs/examples/data/sir_contact_edges.csv
  n_nodes: 500
  initially_infected: 5
  p_infect: 0.08
  p_recover: 0.03
  t_end: 120
```

**Metrics:**

- `susceptible_count`
- `infected_count`
- `recovered_count`
- `new_infections`
- `new_recoveries`
- `r_effective_estimate`

**Events:**

- `infection`
- `recovery`

---

## 2. Version 1 Implementation Task List

This task list is intentionally detailed enough to take the project from an empty repo to a complete first runnable simulation system. Each checkpoint should leave the project in a working state.

### Checkpoint 0 — Repository initialization

- [ ] Create the initial git commit with the architecture document.
- [ ] Add `.gitignore` for Python, Node, virtual environments, build outputs, caches, and local run artefacts while keeping `runs/.gitkeep`.
- [ ] Add `README.md` with project purpose, v1 status, quickstart placeholder, and architecture link.
- [ ] Add `LICENSE` and choose the license before accepting external contributions.
- [ ] Add `CONTRIBUTING.md` with dev setup, test commands, and plugin contribution policy.
- [ ] Add `CODE_OF_CONDUCT.md` if the project will accept community contributions.
- [ ] Add `.editorconfig` for consistent whitespace and newlines.
- [ ] Add `docs/decisions/0001-v1-scope.md` documenting the local-first Version 1 boundary.
- [ ] Verify `git status` is clean after the first commit.

### Checkpoint 1 — Python workspace and tooling

- [x] Create root `pyproject.toml` for the `persephone` engine package.
- [x] Configure Python `>=3.11`.
- [x] Add runtime dependencies: `numpy`, `scipy`, `pydantic`, `typer`, `rich`, `pyyaml`, `packaging`.
- [x] Add development dependencies: `pytest`, `pytest-cov`, `ruff`, `mypy`, `hypothesis`.
- [x] Configure `ruff` formatting and lint rules.
- [x] Configure `mypy` with strict settings for first-party packages.
- [x] Create `src/persephone/__init__.py` with `__version__ = "0.1.0"`.
- [x] Create `tests/test_import.py` proving `import persephone` works.
- [x] Run `uv sync`.
- [x] Run `uv run pytest`.
- [x] Run `uv run ruff check .`.
- [x] Run `uv run mypy src`.
- [ ] Commit: `chore: initialize python workspace`.

### Checkpoint 2 — Plugin SDK package

- [x] Create `sdk/pyproject.toml` for `persephone-sdk`.
- [x] Create `sdk/src/persephone_sdk/__init__.py`.
- [x] Create `sdk/src/persephone_sdk/plugin.py`.
- [x] Define `World`, `Solver`, `Observer`, and `Renderer` abstract base classes.
- [x] Define `PluginManifest` with name, version, paradigm, interface classes, bus reads/writes, params schema, metrics schema, and SDK minimum version.
- [x] Create `sdk/src/persephone_sdk/types.py` for shared `StateDict`, `MetricRecord`, `EventRecord`, and `BusRecord` type aliases.
- [x] Create `sdk/src/persephone_sdk/testing.py` with `PluginTestHarness`.
- [x] Add tests for manifest validation and interface compliance.
- [x] Add tests proving a fake plugin passes the harness.
- [x] Add tests proving a malformed plugin fails with clear errors.
- [x] Run SDK tests.
- [ ] Commit: `feat: add plugin sdk contracts`.

### Checkpoint 3 — Config models and validation

- [x] Create `src/persephone/config/models.py`.
- [x] Define `ExperimentConfig`, `SchedulerConfig`, `SolverConfig`, `ObserverConfig`, `StorageConfig`, and `CouplingConfig` as Pydantic models.
- [x] Add semver/version constraint fields for plugins.
- [x] Add path validation for local data sources.
- [x] Add positive numeric validation for `t_end`, `dt`, probabilities, and ensemble sizes.
- [x] Create `src/persephone/config/load.py` to load YAML and return typed config models.
- [x] Create `src/persephone/config/schema.py` to export JSON Schema.
- [x] Add tests for valid config loading.
- [x] Add tests for missing required fields.
- [x] Add tests for invalid probabilities and missing data paths.
- [x] Add `persephone validate <config>` CLI command stub wired to validation.
- [ ] Commit: `feat: validate experiment configs`.

### Checkpoint 4 — Plugin registry

- [x] Create `src/persephone/registry/registry.py`.
- [x] Discover plugins through `importlib.metadata.entry_points(group="persephone.plugins")`.
- [x] Load plugin manifests without instantiating worlds or solvers.
- [x] Catch and report broken plugin imports without crashing discovery.
- [x] Validate `sdk_min_version` and requested experiment plugin version constraints.
- [x] Add `PluginRegistry.list_all()`, `get(name)`, and `require(name, version_constraint)`.
- [x] Add tests using fake entry points.
- [x] Add tests for incompatible SDK versions.
- [x] Add tests for missing plugin error messages.
- [x] Add `persephone plugins list`.
- [ ] Commit: `feat: discover installed plugins`.

### Checkpoint 5 — Double-buffered in-memory data bus

- [x] Create `src/persephone/core/bus.py`.
- [x] Implement `BusChannelSchema`.
- [x] Implement `InMemoryDataBus.read(channel)` against committed state.
- [x] Implement `InMemoryDataBus.write(channel, value, solver_id, tick)` against pending state.
- [x] Implement `commit(tick)` to validate pending writes and promote them atomically.
- [x] Implement conflict detection for duplicate writes without a declared coupling rule.
- [x] Implement coupling rules: `sum`, `mean`, `max`, `min`, and `last`.
- [x] Add shape and dtype validation for writes.
- [x] Add tests proving current-tick writes are invisible until commit.
- [x] Add tests for each coupling rule.
- [x] Add tests for schema violations.
- [ ] Commit: `feat: add deterministic data bus`.

### Checkpoint 6 — Run context, seed plan, and artefact store

- [x] Create `src/persephone/core/run.py`.
- [x] Define `RunContext` with `run_id`, config snapshot, config hash, engine version, SDK version, plugin versions, start time, status, and seed plan.
- [x] Create deterministic per-solver RNG substreams using `numpy.random.SeedSequence`.
- [x] Create `src/persephone/storage/artifacts.py`.
- [x] Implement local run directory creation under `runs/<run_id>/`.
- [x] Write immutable `manifest.json` at run start and update status on completion or failure.
- [x] Write `metrics.jsonl`.
- [x] Write `events.jsonl`.
- [x] Write final state as `.npz` where possible and JSON metadata alongside it.
- [x] Add tests for manifest contents.
- [x] Add tests proving the same seed plan is regenerated from the same config.
- [ ] Commit: `feat: add run provenance and artifacts`.

### Checkpoint 7 — Graph solver kernel

- [x] Create `src/persephone/solvers/graph.py`.
- [x] Implement a lightweight `ContactGraph` loader from CSV edge list.
- [x] Support weighted undirected edges for Version 1.
- [x] Implement SIR propagation with deterministic RNG input.
- [x] Ensure all state transitions are computed from the previous state, not partially updated state.
- [x] Emit infection and recovery events.
- [x] Add tests for graph loading.
- [x] Add tests for no infection when `p_infect = 0`.
- [x] Add tests for guaranteed infection when `p_infect = 1` on a simple graph.
- [x] Add tests for deterministic output with the same seed.
- [ ] Commit: `feat: add graph sir kernel`.

### Checkpoint 8 — Scheduler

- [x] Create `src/persephone/core/scheduler.py`.
- [x] Implement a single-process scheduler for Version 1.
- [x] Advance logical time from `0` to `t_end` using fixed graph ticks.
- [x] Call each active solver with `state`, `dt`, `bus`, and solver RNG.
- [x] Commit bus writes after every tick.
- [x] Call observers after every committed tick.
- [x] Stop cleanly on completion, cancellation, or solver error.
- [x] Record failed run status and error message in `manifest.json`.
- [x] Add tests for exact tick count.
- [x] Add tests for observer emission cadence.
- [x] Add tests for solver exceptions producing failed manifests.
- [ ] Commit: `feat: add local scheduler`.

### Checkpoint 9 — Engine facade

- [x] Create `src/persephone/core/engine.py`.
- [x] Implement `PersephoneEngine.validate(config)`.
- [x] Implement `PersephoneEngine.run(config)`.
- [x] Resolve plugin manifests from the registry.
- [x] Instantiate plugin world, solver, observer, and renderer classes.
- [x] Validate bus reads/writes before run start.
- [x] Build `RunContext`, scheduler, bus, and artefact store.
- [x] Return a `RunResult` with run id, status, artefact path, final time, and metric summary.
- [x] Add integration tests with a fake plugin.
- [ ] Commit: `feat: wire engine facade`.

### Checkpoint 10 — First plugin package

- [ ] Create `plugins/persephone-plugin-sir-epidemic/pyproject.toml`.
- [ ] Declare the entry point group `persephone.plugins`.
- [ ] Create `plugins/persephone-plugin-sir-epidemic/src/persephone_sir_epidemic/__init__.py`.
- [ ] Implement `SIRWorld` that loads `source,target,weight` CSV data.
- [ ] Implement `SIRSolver` using the graph kernel.
- [ ] Implement `SIRObserver` returning counts and transition events.
- [ ] Implement `SIRRenderer.viz_schema()` for graph and count chart hints.
- [ ] Implement `SIREpidemicPlugin.manifest()`.
- [ ] Add default params and parameter schema.
- [ ] Add plugin tests using `PluginTestHarness`.
- [ ] Add scientific sanity tests for conservation: `S + I + R = n_nodes` for every tick.
- [ ] Install the plugin editable in dev docs: `uv pip install -e plugins/persephone-plugin-sir-epidemic`.
- [ ] Confirm `persephone plugins list` discovers it.
- [ ] Commit: `feat: add sir epidemic plugin`.

### Checkpoint 11 — Ready data source and example config

- [ ] Create `configs/examples/data/sir_contact_edges.csv`.
- [ ] Keep the example network small enough for fast tests and large enough for non-trivial spread.
- [ ] Create `configs/examples/sir_epidemic.yaml`.
- [ ] Set seed, `t_end`, graph path, infection probability, recovery probability, and initial infected count.
- [ ] Add `configs/examples/README.md` explaining the data source and expected output.
- [ ] Add optional generator command `persephone examples generate-sir-network`.
- [ ] Add tests that the example config validates.
- [ ] Add an integration test that runs the example to completion in under a few seconds.
- [ ] Commit: `feat: add runnable sir example`.

### Checkpoint 12 — CLI run, inspect, and replay

- [ ] Create `src/persephone/cli/main.py`.
- [ ] Implement `persephone validate <config>`.
- [ ] Implement `persephone run <config>`.
- [ ] Implement `persephone runs show <run_id_or_path>`.
- [ ] Implement `persephone runs metrics <run_id_or_path> --metric infected_count`.
- [ ] Implement `persephone replay <run_id_or_path>` that reads artefacts and prints a compact time-series summary.
- [ ] Add rich terminal tables for plugin lists and run summaries.
- [ ] Add CLI tests with Typer's test runner.
- [ ] Commit: `feat: add simulation cli`.

### Checkpoint 13 — Local API, optional but useful for v1

- [ ] Decide whether Version 1 includes the API or ships CLI-only.
- [ ] If included, create a minimal Python FastAPI service or defer Hono until frontend work begins.
- [ ] Implement `GET /health`.
- [ ] Implement `GET /plugins`.
- [ ] Implement `POST /runs`.
- [ ] Implement `GET /runs/{run_id}`.
- [ ] Implement `GET /runs/{run_id}/metrics`.
- [ ] Add API tests.
- [ ] Document that production auth is out of scope for Version 1.
- [ ] Commit: `feat: add local run api`.

### Checkpoint 14 — Documentation

- [ ] Update `README.md` with a real quickstart.
- [ ] Document the package boundaries: engine, SDK, plugin.
- [ ] Document the plugin trust model for Version 1.
- [ ] Document the SIR plugin API and CSV schema.
- [ ] Document run artefact layout.
- [ ] Document reproducibility guarantees and limits.
- [ ] Add troubleshooting for missing plugin entry points.
- [ ] Add `docs/plugin-authoring.md`.
- [ ] Add `docs/config-reference.md`.
- [ ] Commit: `docs: add v1 user and plugin docs`.

### Checkpoint 15 — Quality gate

- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run ruff format --check .`.
- [ ] Run `uv run mypy src sdk/src plugins/persephone-plugin-sir-epidemic/src`.
- [ ] Run `uv run pytest --cov`.
- [ ] Run `persephone validate configs/examples/sir_epidemic.yaml`.
- [ ] Run `persephone plugins list`.
- [ ] Run `persephone run configs/examples/sir_epidemic.yaml`.
- [ ] Run the same config twice with the same seed and compare metrics.
- [ ] Run the same config with a different seed and confirm stochastic outcomes differ.
- [ ] Inspect `runs/<run_id>/manifest.json`.
- [ ] Inspect `runs/<run_id>/metrics.jsonl`.
- [ ] Create a release checklist in `docs/release-v0.1.md`.
- [ ] Commit: `test: complete v1 quality gate`.

### Checkpoint 16 — Version 1 release

- [ ] Tag the release as `v0.1.0`.
- [ ] Build source and wheel distributions for `persephone`, `persephone-sdk`, and `persephone-plugin-sir-epidemic`.
- [ ] Install from built wheels in a clean virtual environment.
- [ ] Run the quickstart from the README in that clean environment.
- [ ] Archive example run artefacts under `docs/examples/sir-run-output/` or link to a generated sample.
- [ ] Write release notes with capabilities, known limitations, and next priorities.
- [ ] Commit release documentation.

### Post-v1 checkpoint — next high-leverage improvements

- [ ] Add ODE wrapper with `scipy.solve_ivp`.
- [ ] Add PDE heat diffusion plugin and data source.
- [ ] Add SDE ensemble mode.
- [ ] Add Redis bus backend using a safe serialization format.
- [ ] Add TimescaleDB metric sink.
- [ ] Add Hono API and Svelte UI after the CLI kernel is proven.
- [ ] Add parameter sweeps.
- [ ] Add checkpoint/resume.
- [ ] Add plugin packaging templates.
- [ ] Revisit sandboxing and remote plugin installation.

---
