# Persephone Version 2 Task List

## 1. Version 2 Product Aim

Version 1 proves the local simulation kernel: config validation, plugin discovery, SIR plugin execution, metrics/events, artifacts, and CLI inspection.

Version 2 should turn Persephone into a **local research workbench**:

> A researcher can start a local API, open a browser UI, choose or edit an experiment config, run simulations and parameter sweeps, watch live metrics, compare runs, export results, and use at least two simulation paradigms through real plugins.

This is the right next target because v1 already answers "can the engine run?" Version 2 should answer "can a person use this repeatedly to explore ideas?"

## 2. Recommended Scope

### In scope for v2

- Local API service for running, listing, inspecting, and streaming simulations.
- Web UI for experiment editing, running, metrics visualization, run history, and replay, built with SvelteKit, TypeScript, and shadcn-svelte.
- Run catalog/index so artifacts can be discovered without manually passing paths.
- Parameter sweeps for simple scalar parameters.
- Run comparison tools.
- Export to CSV and Parquet.
- A second plugin using a different paradigm: heat diffusion PDE.
- Plugin template/scaffolding command.
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
- [ ] `GET /runs/{run_id}/stream` streams live metric events during active runs.
- [ ] Web UI can create or load the SIR example config.
- [ ] Web UI can run the simulation and show live metric charts.
- [ ] Web UI can replay a completed run.
- [ ] Web UI can compare at least two runs on the same chart.
- [ ] Parameter sweep can run at least one scalar parameter across multiple values.
- [ ] Heat diffusion PDE plugin runs from an example config and produces field metrics.
- [ ] Results can be exported to CSV and Parquet.
- [ ] Same-seed reproducibility remains covered by tests.
- [ ] Full test, lint, format, type, and UI build checks pass.

---

## 5. Version 2 Implementation Task List

### Checkpoint 0 — v1 stabilization before v2

- [ ] Commit or intentionally squash all completed v1 work.
- [ ] Confirm `git status` is clean before v2 work begins.
- [ ] Run `uv sync`.
- [ ] Run `uv run pytest --cov`.
- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run ruff format --check .`.
- [ ] Run `uv run mypy src sdk/src plugins/persephone-plugin-sir-epidemic/src`.
- [ ] Run `uv run persephone run configs/examples/sir_epidemic.yaml --run-id v2-baseline`.
- [ ] Save one known-good baseline output summary in `docs/examples/v1-baseline.md`.
- [ ] Commit: `chore: stabilize v1 baseline`.

### Checkpoint 1 — Run catalog and artifact discovery

- [ ] Create `src/persephone/storage/catalog.py`.
- [ ] Implement `RunCatalog.scan(root)` to discover run directories containing `manifest.json`.
- [ ] Implement `RunCatalog.list_runs()` sorted by start time descending.
- [ ] Implement `RunCatalog.get(run_id_or_path)`.
- [ ] Implement status filtering: `completed`, `failed`, `running`.
- [ ] Add manifest summary model: run id, name, status, started time, final time, plugin names, config hash.
- [ ] Update `persephone runs show` to accept run id from the catalog, not only a path.
- [ ] Update `persephone runs metrics` to accept run id from the catalog.
- [ ] Add tests for catalog scanning.
- [ ] Add tests for duplicate run ids across roots.
- [ ] Commit: `feat: add local run catalog`.

### Checkpoint 2 — Local API service

- [ ] Add FastAPI and Uvicorn dependencies.
- [ ] Create `src/persephone/api/app.py`.
- [ ] Create `src/persephone/api/routes/health.py`.
- [ ] Create `src/persephone/api/routes/plugins.py`.
- [ ] Create `src/persephone/api/routes/runs.py`.
- [ ] Implement `GET /health`.
- [ ] Implement `GET /plugins`.
- [ ] Implement `POST /runs` accepting an experiment config payload.
- [ ] Implement `GET /runs`.
- [ ] Implement `GET /runs/{run_id}`.
- [ ] Implement `GET /runs/{run_id}/metrics`.
- [ ] Implement `GET /runs/{run_id}/events`.
- [ ] Add `persephone api --host 127.0.0.1 --port 8787`.
- [ ] Add API tests using FastAPI test client.
- [ ] Document local-only security posture.
- [ ] Commit: `feat: add local api service`.

### Checkpoint 3 — Live run execution and metric streaming

- [ ] Add a `RunManager` that tracks active local runs.
- [ ] Run simulations in a background thread or task.
- [ ] Add run cancellation state to `RunManager`.
- [ ] Add active run status endpoint.
- [ ] Add `GET /runs/{run_id}/stream` using Server-Sent Events.
- [ ] Emit metric events from the scheduler as they are written.
- [ ] Add scheduler callback hook for metrics/events.
- [ ] Add tests for active run status transitions.
- [ ] Add tests that stream emits metric events.
- [ ] Add tests for failed runs preserving error messages.
- [ ] Commit: `feat: stream live run metrics`.

### Checkpoint 4 — UI workspace setup

- [ ] Create `ui/` with SvelteKit and TypeScript.
- [ ] Configure Vite.
- [ ] Configure Svelte 5.
- [ ] Install and configure shadcn-svelte from `https://www.shadcn-svelte.com/`.
- [ ] Configure Tailwind CSS as required by shadcn-svelte.
- [ ] Add initial shadcn-svelte components needed for v2: button, card, table, tabs, dialog, select, input, textarea, badge, alert, separator, sheet, skeleton, and tooltip.
- [ ] Define a small Persephone UI theme using shadcn-svelte tokens.
- [ ] Add UI package scripts: `dev`, `build`, `check`, `test`.
- [ ] Add API base URL environment variable.
- [ ] Add typed API client in `ui/src/lib/api.ts`.
- [ ] Add basic app shell with navigation for Runs, Experiments, Plugins, and Settings.
- [ ] Add Playwright or Vitest for UI checks.
- [ ] Commit: `feat: initialize ui workspace`.

### Checkpoint 5 — Run dashboard UI

- [ ] Build a run list page.
- [ ] Show run status, experiment name, plugin, start time, final time, and artifact location.
- [ ] Build run detail page.
- [ ] Render manifest metadata.
- [ ] Render metric chart for `susceptible_count`, `infected_count`, and `recovered_count`.
- [ ] Render event table for infection and recovery events.
- [ ] Add empty state when no runs exist.
- [ ] Add loading and error states for API failures.
- [ ] Add UI tests for run list and detail rendering.
- [ ] Commit: `feat: add run dashboard`.

### Checkpoint 6 — Experiment editor UI

- [ ] Build experiment editor page.
- [ ] Load `configs/examples/sir_epidemic.yaml` through the API or a bundled example endpoint.
- [ ] Show editable fields for seed, `t_end`, `p_infect`, `p_recover`, and initially infected nodes.
- [ ] Validate config client-side using exported JSON Schema.
- [ ] Show validation errors inline.
- [ ] Add a Run button that calls `POST /runs`.
- [ ] Show the created run id and link to run detail page.
- [ ] Add UI tests for editing and submitting a config.
- [ ] Commit: `feat: add experiment editor`.

### Checkpoint 7 — Live metrics UI

- [ ] Connect run detail page to `/runs/{run_id}/stream`.
- [ ] Update chart as metric events arrive.
- [ ] Show run status as pending, running, completed, or failed.
- [ ] Show elapsed logical simulation time.
- [ ] Handle stream reconnect or graceful completion.
- [ ] Add a compact metric summary: peak infected, final recovered, duration.
- [ ] Add UI tests for streamed metric updates.
- [ ] Commit: `feat: add live metrics UI`.

### Checkpoint 8 — Parameter sweeps

- [ ] Define sweep config schema.
- [ ] Support scalar parameter sweeps using dotted paths like `solvers[0].params.p_infect`.
- [ ] Generate run configs for each sweep value.
- [ ] Execute sweep runs sequentially first.
- [ ] Store sweep manifest under `runs/<sweep_id>/sweep.json`.
- [ ] Link child runs to sweep id in their manifests.
- [ ] Add CLI command `persephone sweep <sweep.yaml>`.
- [ ] Add API endpoint `POST /sweeps`.
- [ ] Add UI sweep form for one scalar parameter.
- [ ] Add tests for config generation and run linking.
- [ ] Commit: `feat: add parameter sweeps`.

### Checkpoint 9 — Run comparison

- [ ] Add metric alignment utility for comparing runs by metric name and time.
- [ ] Add CLI command `persephone compare <run_a> <run_b> --metric infected_count`.
- [ ] Add API endpoint `GET /compare?run=a&run=b&metric=infected_count`.
- [ ] Add UI comparison page with overlay line charts.
- [ ] Show peak, final value, and area-under-curve summary for each run.
- [ ] Add tests for metric alignment with missing time points.
- [ ] Commit: `feat: compare run metrics`.

### Checkpoint 10 — Results export

- [ ] Add CSV export for metrics and events.
- [ ] Add Parquet export for metrics and events.
- [ ] Add dependency for Parquet support, such as `pyarrow`.
- [ ] Implement `persephone export <run> --format csv`.
- [ ] Implement `persephone export <run> --format parquet`.
- [ ] Add API endpoint for export download.
- [ ] Add UI export button.
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
- [ ] Add API/UI support for field metrics.
- [ ] Commit: `feat: add heat diffusion plugin`.

### Checkpoint 12 — Field visualization UI

- [ ] Add field artifact support for selected snapshots.
- [ ] Add heatmap canvas component.
- [ ] Render final heat field from `final_state.npz`.
- [ ] Add color scale legend.
- [ ] Add min/max/mean overlays.
- [ ] Add UI tests for heatmap rendering.
- [ ] Commit: `feat: add field visualization`.

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
- [ ] Add screenshots or rendered UI previews if available.
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
