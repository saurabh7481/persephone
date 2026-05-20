# Persephone Version 2 Task List

## 1. Version 2 Product Aim

Version 1 proves the local simulation kernel: config validation, plugin discovery, SIR plugin execution, metrics/events, artifacts, and CLI inspection.

Version 2 should turn Persephone into a **headless-first local research workbench**:

> A researcher can start a local API, open a browser UI, choose or edit an experiment config, run simulations and parameter sweeps, watch live metrics, compare runs, export results, and use at least two simulation paradigms through real plugins.

This is the right next target because v1 already answers "can the engine run?" Version 2 should answer "can a person use this repeatedly to explore ideas?"

Before continuing with export, field visualization, or additional simulation paradigms, Version 2 must harden the core architecture. The current SIR vertical slice is useful, but the scheduler, state contract, bus schemas, telemetry, checkpointing, and solver-wrapper boundaries need to become robust enough to support long-running and multi-paradigm simulations without hidden assumptions.

The current Svelte UI is an MVP smoke-test client, not the final product surface. From this point in v2, prioritize engine, plugin, CLI, API, artifact, export, and schema capabilities. Keep the MVP UI compiling and passing tests, but defer major UI feature work until the new UI is designed on top of a stable API.

## 2. Recommended Scope

### In scope for v2

- Local API service for running, listing, inspecting, and streaming simulations.
- MVP web UI for experiment editing, running, metrics visualization, run history, and replay, built with SvelteKit, TypeScript, and shadcn-svelte.
- Run catalog/index so artifacts can be discovered without manually passing paths.
- Parameter sweeps for simple scalar parameters.
- Run comparison tools.
- Core architecture hardening: typed records, scheduler telemetry, checkpoint/resume groundwork, state typing, stricter bus/coupling validation, and manifest-driven solver-wrapper contracts.
- Export to CSV and Parquet through CLI/API first.
- A second plugin using a different paradigm: heat diffusion PDE.
- Plugin template/scaffolding command.
- Stable API and schema contracts for a future full UI rewrite.
- Stronger docs, examples, and release packaging.

### Out of scope for v2

- GPU acceleration.
- Rust engine core.
- MPI or cluster execution.
- Kubernetes deployment.
- Multi-user auth.
- Remote plugin marketplace.
- Untrusted plugin sandboxing.
- TimescaleDB, ClickHouse, Redis, or S3 as required runtime dependencies.
- Major redesign or expansion of the MVP UI.

Those are valuable, but they are scale and ecosystem work. Version 2 should first make the local experience excellent.

## 3. API Direction

The original long-term architecture mentions Hono.js. For Version 2, use a Python local API first, most likely FastAPI, because the engine is Python and can run in-process without a TypeScript/Python bridge. Keep the API surface clean enough that a future Hono gateway can proxy or replace it later.

The API should be local-first and unauthenticated by default:

- Bound to `127.0.0.1`.
- No production auth in v2.
- Explicit warning if binding to non-localhost.

## 4. Version 2 Acceptance Criteria

- [ ] `persephone api` starts a local API server.
- [ ] `GET /health` returns service status and version.
- [ ] `GET /plugins` returns `sir_epidemic` and any installed plugins.
- [ ] `POST /runs` starts a run from a config payload.
- [ ] `GET /runs` lists previous runs from the local run catalog.
- [ ] `GET /runs/{run_id}` returns manifest and status.
- [ ] `GET /runs/{run_id}/metrics` returns metrics as JSON.
- [ ] `GET /runs/{run_id}/events` returns events as JSON.
- [x] `GET /runs/{run_id}/stream` streams live metric events during active runs.
- [x] Web UI can create or load the SIR example config.
- [x] Web UI can run the simulation and show live metric charts.
- [x] Web UI can replay a completed run.
- [x] Web UI can compare at least two runs on the same chart.
- [x] Parameter sweep can run at least one scalar parameter across multiple values.
- [x] Core records are typed: metrics, events, scheduler telemetry, run manifests, state values, and bus records.
- [x] Scheduler honors configured synchronization and observation cadence.
- [x] Scheduler emits internal telemetry for performance and coupling debugging.
- [x] Runs can write checkpoint snapshots with state, bus, RNG, and manifest metadata.
- [x] Core solver wrappers are manifest-driven and contain no domain-specific bus channel names.
- [ ] Heat diffusion PDE plugin runs from an example config and produces field metrics.
- [ ] Results can be exported to CSV and Parquet.
- [ ] Same-seed reproducibility remains covered by tests.
- [ ] Full test, lint, format, type, and UI build checks pass.
- [x] Docker Compose runs the local API and UI together.

---

## 5. Version 2 Implementation Task List

### Checkpoint 0 — v1 stabilization before v2

- [x] Commit or intentionally squash all completed v1 work.
- [x] Confirm `git status` is clean before v2 work begins.
- [x] Run `uv sync`.
- [x] Run `uv run pytest --cov`.
- [x] Run `uv run ruff check .`.
- [x] Run `uv run ruff format --check .`.
- [x] Run `uv run mypy src sdk/src plugins/persephone-plugin-sir-epidemic/src`.
- [x] Run `uv run persephone run configs/examples/sir_epidemic.yaml --run-id v2-baseline`.
- [x] Save one known-good baseline output summary in `docs/examples/v1-baseline.md`.
- [ ] Commit: `chore: stabilize v1 baseline`.

### Checkpoint 1 — Run catalog and artifact discovery

- [x] Create `src/persephone/storage/catalog.py`.
- [x] Implement `RunCatalog.scan(root)` to discover run directories containing `manifest.json`.
- [x] Implement `RunCatalog.list_runs()` sorted by start time descending.
- [x] Implement `RunCatalog.get(run_id_or_path)`.
- [x] Implement status filtering: `completed`, `failed`, `running`.
- [x] Add manifest summary model: run id, name, status, started time, final time, plugin names, config hash.
- [x] Update `persephone runs show` to accept run id from the catalog, not only a path.
- [x] Update `persephone runs metrics` to accept run id from the catalog.
- [x] Add tests for catalog scanning.
- [x] Add tests for duplicate run ids across roots.
- [ ] Commit: `feat: add local run catalog`.

### Checkpoint 2 — Local API service

- [x] Add FastAPI and Uvicorn dependencies.
- [x] Create `src/persephone/api/app.py`.
- [x] Create `src/persephone/api/routes/health.py`.
- [x] Create `src/persephone/api/routes/plugins.py`.
- [x] Create `src/persephone/api/routes/runs.py`.
- [x] Implement `GET /health`.
- [x] Implement `GET /plugins`.
- [x] Implement `POST /runs` accepting an experiment config payload.
- [x] Implement `GET /runs`.
- [x] Implement `GET /runs/{run_id}`.
- [x] Implement `GET /runs/{run_id}/metrics`.
- [x] Implement `GET /runs/{run_id}/events`.
- [x] Add `persephone api --host 127.0.0.1 --port 8787`.
- [x] Add API tests using FastAPI test client.
- [x] Document local-only security posture.
- [ ] Commit: `feat: add local api service`.

### Checkpoint 3 — Live run execution and metric streaming

- [x] Add a `RunManager` that tracks active local runs.
- [x] Run simulations in a background thread or task.
- [x] Add run cancellation state to `RunManager`.
- [x] Add active run status endpoint.
- [x] Add `GET /runs/{run_id}/stream` using Server-Sent Events.
- [x] Emit metric events from the scheduler as they are written.
- [x] Add scheduler callback hook for metrics/events.
- [x] Add tests for active run status transitions.
- [x] Add tests that stream emits metric events.
- [x] Add tests for failed runs preserving error messages.
- [ ] Commit: `feat: stream live run metrics`.

### Checkpoint 4 — UI workspace setup

- [x] Create `ui/` with SvelteKit and TypeScript.
- [x] Configure Vite.
- [x] Configure Svelte 5.
- [x] Install and configure shadcn-svelte from `https://www.shadcn-svelte.com/`.
- [x] Configure Tailwind CSS as required by shadcn-svelte.
- [x] Add initial shadcn-svelte components needed for v2: button, card, table, tabs, dialog, select, input, textarea, badge, alert, separator, sheet, skeleton, and tooltip.
- [x] Define a small Persephone UI theme using shadcn-svelte tokens.
- [x] Add UI package scripts: `dev`, `build`, `check`, `test`.
- [x] Add API base URL environment variable.
- [x] Add typed API client in `ui/src/lib/api.ts`.
- [x] Add basic app shell with navigation for Runs, Experiments, Plugins, and Settings.
- [x] Add Playwright or Vitest for UI checks.
- [ ] Commit: `feat: initialize ui workspace`.

### Checkpoint 5 — Run dashboard UI

- [x] Build a run list page.
- [x] Show run status, experiment name, plugin, start time, final time, and artifact location.
- [x] Build run detail page.
- [x] Render manifest metadata.
- [x] Render metric chart for `susceptible_count`, `infected_count`, and `recovered_count`.
- [x] Render event table for infection and recovery events.
- [x] Add empty state when no runs exist.
- [x] Add loading and error states for API failures.
- [x] Add UI tests for run list and detail rendering.
- [ ] Commit: `feat: add run dashboard`.

### Checkpoint 6 — Experiment editor UI

- [x] Build experiment editor page.
- [x] Load `configs/examples/sir_epidemic.yaml` through the API or a bundled example endpoint.
- [x] Show editable fields for seed, `t_end`, `p_infect`, `p_recover`, and initially infected nodes.
- [x] Validate config client-side using exported JSON Schema.
- [x] Show validation errors inline.
- [x] Add a Run button that calls `POST /runs`.
- [x] Show the created run id and link to run detail page.
- [x] Add UI tests for editing and submitting a config.
- [ ] Commit: `feat: add experiment editor`.

### Checkpoint 7 — Live metrics UI

- [x] Connect run detail page to `/runs/{run_id}/stream`.
- [x] Update chart as metric events arrive.
- [x] Show run status as pending, running, completed, or failed.
- [x] Show elapsed logical simulation time.
- [x] Handle stream reconnect or graceful completion.
- [x] Add a compact metric summary: peak infected, final recovered, duration.
- [x] Add UI tests for streamed metric updates.
- [ ] Commit: `feat: add live metrics UI`.

### Checkpoint 7A — Dockerized local stack

- [x] Add API Dockerfile.
- [x] Add UI Dockerfile using Bun.
- [x] Add Docker Compose stack for API and UI.
- [x] Persist local run artifacts through a host-mounted `runs/` volume.
- [x] Add Docker smoke tests or config tests.
- [x] Document Docker quickstart.
- [ ] Commit: `feat: dockerize local workbench`.

### Checkpoint 8 — Parameter sweeps

- [x] Define sweep config schema.
- [x] Support scalar parameter sweeps using dotted paths like `solvers[0].params.p_infect`.
- [x] Generate run configs for each sweep value.
- [x] Execute sweep runs sequentially first.
- [x] Store sweep manifest under `runs/<sweep_id>/sweep.json`.
- [x] Link child runs to sweep id in their manifests.
- [x] Add CLI command `persephone sweep <sweep.yaml>`.
- [x] Add API endpoint `POST /sweeps`.
- [x] Add UI sweep form for one scalar parameter.
- [x] Add tests for config generation and run linking.
- [ ] Commit: `feat: add parameter sweeps`.

### Checkpoint 9 — Run comparison

- [x] Add metric alignment utility for comparing runs by metric name and time.
- [x] Add CLI command `persephone compare <run_a> <run_b> --metric infected_count`.
- [x] Add API endpoint `GET /compare?run=a&run=b&metric=infected_count`.
- [x] Add UI comparison page with overlay line charts.
- [x] Show peak, final value, and area-under-curve summary for each run.
- [x] Add tests for metric alignment with missing time points.
- [ ] Commit: `feat: compare run metrics`.

### Checkpoint 9A — Core architecture hardening

This checkpoint is mandatory before Checkpoint 10 or any new simulation paradigm work. It turns the current local workbench core into a sturdier simulation kernel that can support exports, PDE fields, ODE/SDE wrappers, longer runs, and future distributed execution.

#### 9A.1 Typed SDK and core records

- [x] Replace loose `dict[str, Any]` metric/event aliases with typed models or dataclasses for `MetricRecord` and `EventRecord`.
- [x] Add `SchedulerTelemetry` schema with tick, logical time, wall time, sync interval used, per-solver timing, bus conflict counts, and bus channel sizes.
- [x] Add a typed `RunManifest` schema matching persisted `manifest.json`.
- [x] Add `StateValue` and `WorldState` type aliases that explicitly describe supported state values.
- [x] Add `BusRecord` and `BusChannelSchema` fields for value kind, schema version, units, shape, dtype, and semantic channel metadata.
- [x] Export JSON Schema for API/UI consumers where useful.
- [x] Add tests that invalid metric/event/manifest records fail validation before they reach storage.

#### 9A.2 Scheduler semantics and operator splitting

- [x] Make scheduler honor `scheduler.sync_interval` instead of always using the minimum solver `preferred_dt`.
- [x] Make scheduler honor optional `scheduler.dt` where applicable.
- [x] Make scheduler honor `observer.emit_every` so observers are not forced to emit every internal tick.
- [x] Validate solver returned elapsed time against the requested step semantics.
- [x] Update global logical time from the validated elapsed interval, not from an unchecked requested interval.
- [x] Document first-order operator splitting behavior in scheduler docs.
- [x] Add `splitting_order` to scheduler config with `first_order` implemented first and `strang` reserved for later.
- [ ] Emit a validation warning or error when tight-coupling configs request unsafe sync intervals.
- [x] Add scheduler tests for sync interval, observer cadence, elapsed-time validation, and splitting-order validation.

#### 9A.3 Scheduler telemetry

- [x] Time each solver step and each scheduler tick.
- [x] Emit scheduler telemetry records through the same metric/event pipeline used by domain metrics.
- [x] Track whether a solver constrained the step size, preparing for PDE CFL constraints.
- [x] Track multi-writer bus conflicts and the coupling rule used to resolve each channel.
- [x] Estimate committed bus channel sizes to detect unexpected state growth.
- [x] Expose scheduler telemetry through existing CLI/API metric inspection paths.
- [x] Add UI-safe metric naming for scheduler telemetry, such as `scheduler.wall_time_ms`.
- [x] Add tests that telemetry is written for successful and failed runs.

#### 9A.4 Checkpoint and resume groundwork

- [x] Add `checkpoint_every` to scheduler config.
- [x] Add checkpoint artifact layout under `runs/<run_id>/checkpoints/<tick>/`.
- [x] Save full world state for every runtime at checkpoint time.
- [x] Save committed bus snapshot at checkpoint time.
- [x] Save RNG state for every solver runtime.
- [x] Save checkpoint manifest metadata: run id, tick, logical time, engine version, plugin versions, config hash, and checkpoint schema version.
- [x] Ensure failed and cancelled runs remain inspectable up to the last completed checkpoint.
- [x] Add internal restore API for reconstructing scheduler state from a checkpoint.
- [x] Add CLI planning stub or hidden/internal command for checkpoint inspection before exposing full resume UX.
- [x] Add tests for checkpoint file creation, RNG state persistence, bus snapshot persistence, and manifest metadata.

#### 9A.5 Storage sink boundary

- [x] Introduce engine-owned `MetricSink`, `EventSink`, `TelemetrySink`, and `StateSink` interfaces.
- [x] Move JSONL metric/event persistence behind sink implementations.
- [x] Move NPZ/final-state persistence behind a state sink.
- [x] Use atomic write patterns for JSON manifest and checkpoint metadata files.
- [x] Keep plugin observers storage-agnostic: observers only return records.
- [x] Add tests that sinks receive records in deterministic order.
- [x] Add tests that partial write failures mark the run failed with a clear storage error.

#### 9A.6 Bus and coupling hardening

- [x] Preserve the existing double-buffered read/write/commit contract.
- [x] Validate coupling rules at config load time rather than failing late at bus commit.
- [x] Add a coupling registry for named merge functions, while keeping `sum`, `mean`, `max`, `min`, and `last`.
- [ ] Reject numerically unsafe keyword coupling for structured state unless the channel schema permits it.
- [x] Add explicit unsupported-feature errors for sparse matrices and masked arrays until full support lands.
- [x] Add bus snapshot serialization and deserialization for checkpoints.
- [x] Add tests for invalid coupling rules, structured-state rejection, commit conflict telemetry, and bus snapshot round-trips.

#### 9A.7 State contract expansion

- [x] Define the intended long-term state contract: `np.ndarray`, `scipy.sparse.spmatrix`, and `np.ma.MaskedArray`.
- [x] Implement robust support for plain `np.ndarray` first.
- [x] Add explicit validation errors for unsupported sparse/masked state in bus and storage paths.
- [x] Keep final-state metadata extensible enough to represent sparse and masked state later.
- [x] Add tests that unsupported state values fail with clear messages instead of obscure serialization errors.

#### 9A.8 Domain-agnostic solver-wrapper contracts

- [x] Add shared helper utilities for manifest-driven bus reads and writes.
- [x] Ensure future ODE, PDE, ABM, Graph, and SDE wrappers read only channels declared in `manifest.bus_reads`.
- [x] Ensure wrappers write only channels declared in `manifest.bus_writes`.
- [x] Add tests that core wrapper helpers do not hardcode domain-specific channel names such as `temperature_field`, `aerosol_grid`, `viral_fitness`, or `infection_map`.
- [x] Add plugin harness tests for undeclared bus reads/writes.
- [x] Document that domain-specific channel names belong in plugin manifests and configs, never in core engine code.

#### 9A.9 Reproducibility and trust hardening

- [x] Add same-seed reproducibility tests through the public engine API.
- [x] Add same-seed reproducibility tests across parameter sweep child runs where only the swept parameter changes.
- [x] Record solver RNG state in checkpoints.
- [x] Add docs and CLI/API warnings that v2 Python plugins are trusted code.
- [x] Keep remote plugin installation and WASM sandboxing explicitly out of v2 runtime scope.

- [ ] Commit: `feat: harden core simulation architecture`.

### Checkpoint 10 — Results export

- [ ] Add CSV export for metrics and events.
- [ ] Add Parquet export for metrics and events.
- [ ] Add dependency for Parquet support, such as `pyarrow`.
- [ ] Implement `persephone export <run> --format csv`.
- [ ] Implement `persephone export <run> --format parquet`.
- [ ] Add API endpoint for export download.
- [ ] Defer UI export button to the future UI rewrite.
- [ ] Add tests that exported CSV and Parquet preserve row counts and metric names.
- [ ] Commit: `feat: export run results`.

### Checkpoint 11 — Heat diffusion PDE plugin

- [ ] Create `plugins/persephone-plugin-heat-diffusion/pyproject.toml`.
- [ ] Declare entry point `heat_diffusion`.
- [ ] Implement `HeatWorld` for a 2D temperature grid.
- [ ] Implement explicit finite-difference heat equation step.
- [ ] Enforce CFL stability for `dt`.
- [ ] Implement `HeatObserver` with min, max, mean, total heat, and center temperature.
- [ ] Implement `HeatRenderer` with field visualization schema.
- [ ] Add example config `configs/examples/heat_diffusion.yaml`.
- [ ] Add example initial condition generator.
- [ ] Add plugin harness tests.
- [ ] Add conservation/stability tests.
- [ ] Add API/CLI support for field metrics and artifacts.
- [ ] Commit: `feat: add heat diffusion plugin`.

### Checkpoint 12 — Field artifact API

- [ ] Add field artifact support for selected snapshots.
- [ ] Add field metadata schema: dimensions, dtype, bounds, units, and visualization hints.
- [ ] Store final and selected intermediate fields from `final_state.npz` or checkpoint snapshots.
- [ ] Add CLI commands for listing and exporting field artifacts.
- [ ] Add API endpoints to inspect and download field artifacts.
- [ ] Defer heatmap canvas and polished UI rendering to the future UI rewrite.
- [ ] Add tests for field metadata, snapshot discovery, and API download behavior.
- [ ] Commit: `feat: add field artifact api`.

### Checkpoint 13 — Plugin template command

- [ ] Add `persephone plugins scaffold <name>`.
- [ ] Generate plugin package layout.
- [ ] Generate `pyproject.toml` with entry point.
- [ ] Generate stub `World`, `Solver`, `Observer`, `Renderer`.
- [ ] Generate plugin harness test.
- [ ] Generate README.
- [ ] Add tests that scaffolded plugin imports and passes generated harness tests after install.
- [ ] Commit: `feat: scaffold plugin packages`.

### Checkpoint 14 — Documentation and examples

- [ ] Update README with API and UI quickstart.
- [ ] Add `docs/api-reference.md`.
- [ ] Add `docs/ui-guide.md`.
- [ ] Add `docs/sweeps.md`.
- [ ] Add `docs/run-comparison.md`.
- [ ] Add `docs/exporting-results.md`.
- [ ] Add heat diffusion plugin docs.
- [ ] Add schema/API examples for future UI work.
- [ ] Commit: `docs: add v2 user docs`.

### Checkpoint 15 — Version 2 quality gate

- [ ] Run `uv sync`.
- [ ] Run engine tests with coverage.
- [ ] Run API tests.
- [ ] Run UI tests.
- [ ] Run UI build.
- [ ] Run lint, format, and type checks for Python.
- [ ] Run TypeScript checks.
- [ ] Run `persephone run configs/examples/sir_epidemic.yaml`.
- [ ] Run `persephone run configs/examples/heat_diffusion.yaml`.
- [ ] Run a parameter sweep.
- [ ] Compare two sweep child runs.
- [ ] Export one run to CSV.
- [ ] Export one run to Parquet.
- [ ] Start API and verify `/health`.
- [ ] Start UI and verify dashboard loads.
- [ ] Update `docs/release-v0.2.md`.
- [ ] Commit: `test: complete v2 quality gate`.

---

## 6. Version 3 Candidates

These are valuable, but should wait until after the local workbench is useful:

- Redis-backed bus.
- TimescaleDB metrics sink.
- ClickHouse event sink.
- S3-compatible artifact storage.
- Auth and API keys.
- Multi-user projects.
- Hono gateway.
- Rust core.
- GPU acceleration.
- MPI parameter sweeps.
- Plugin marketplace.
- WASM sandboxing.
