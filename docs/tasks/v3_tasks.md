# Persephone Version 3 Task List

## 1. Version 3 Product Aim

Version 2 made Persephone a headless local research workbench: robust Python engine, typed records, checkpoints, metrics/events, exports, field artifacts, sweeps, run comparison, plugin scaffolding, and an MVP UI.

Version 3 should turn Persephone into a **professional Simulation Studio**:

> A non-technical user can create an experiment, run it, watch the simulation animate live, pause and inspect it, replay it later, compare outcomes, and export results; a technical user can still open the same workspace and inspect schemas, frames, runtime metadata, artifacts, and plugin details.

The centerpiece is **live simulation playback**. Experiment creation and result analysis should orbit the playback viewport, not replace it.

## 2. Architecture Direction

Use a layered product architecture:

```text
SvelteKit Simulation Studio
  shadcn-svelte design system
  D3 analytical charts
  Canvas/WebGL simulation viewport
  generated TypeScript API client
        |
FastAPI Engine API
  OpenAPI contracts
  run control
  frame streaming
  replay artifacts
  plugin/runtime metadata
        |
Engine Runtime Interface
  Python runtime backend now
  Rust runtime backend later
```

### API stance

Keep **FastAPI** as the engine-adjacent API in v3 because the simulation engine and trusted plugins are Python. Make the route handlers thin and contract-driven so a Hono gateway can proxy the same API later.

Do not replace FastAPI with Hono yet. If Hono is introduced in v3, use it only as an optional UI-facing gateway/BFF spike.

### Rust stance

Rust should enter later as a runtime backend or accelerated kernel layer, not as a public API rewrite.

The UI should depend on language-neutral contracts:

- `RunSummary`
- `MetricRecord`
- `EventRecord`
- `SimulationFrame`
- `FrameIndex`
- `ArtifactSummary`
- `PluginCapability`
- `RuntimeCapability`

If Rust changes the external UI API, the API is too close to the Python implementation.

## 3. Rendering Direction

Use each frontend tool for its strongest job:

- **SvelteKit + shadcn-svelte**: shell, navigation, panels, forms, command palette, dialogs, layout state, user flows.
- **Canvas/WebGL**: high-frequency simulation playback: fields, grids, graph states, agents, particles.
- **D3**: scales, axes, timelines, brushing, zooming, line charts, distributions, event markers, overlays.

Svelte should orchestrate playback, not render every animation frame.

## 4. Version 3 Acceptance Criteria

- [ ] A professional Studio shell replaces the MVP UI as the primary product surface.
- [ ] Live frame streaming works from day one for at least one plugin.
- [ ] Replay uses the same playback engine as live streaming.
- [ ] Heat diffusion fields animate live in a canvas viewport.
- [ ] SIR graph state can be replayed or visualized through a normalized graph frame contract.
- [ ] D3 metric timeline is synchronized with playback time.
- [ ] Users can pause, resume, scrub, change speed, and jump to events.
- [ ] Users can inspect a selected field cell, graph node, field layer, or frame.
- [ ] Experiment creation is non-technical by default and technical on demand.
- [ ] API contracts are OpenAPI-backed and exposed to the TypeScript UI through a generated or strongly typed client.
- [ ] FastAPI routes remain thin and runtime-backend agnostic.
- [ ] Run manifests include runtime backend metadata.
- [ ] Core API, CLI, and Studio UI do not hardcode SIR, heat diffusion, or any other plugin/domain assumptions outside examples, tests, and plugin packages.
- [ ] Plugin schemas, renderer metadata, capabilities, and frame contracts drive experiment forms, playback, inspection, and analysis.
- [ ] Docker runs the API and Studio UI together.
- [ ] Full Python and UI quality gates pass.

---

## 5. Version 3 Implementation Task List

### Checkpoint 0 — v2 baseline and branch hygiene

- [x] Confirm all v2 work is committed and pushed.
- [x] Confirm `git status --short` is clean except ignored local scratch files.
- [x] Add `.superpowers/` to `.gitignore` if visual companion artifacts should stay local.
- [x] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv sync`.
- [x] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest`.
- [x] Run `cd ui && bun run check && bun run lint && bun run test:unit && bun run build`.
- [x] Create v3 branch: `codex/v3-simulation-studio`.
- [ ] Commit: `chore: start v3 simulation studio`.

### Checkpoint 1 — Engine runtime boundary

- [x] Add `src/persephone/runtime/interface.py`.
- [x] Define `SimulationRuntime` protocol with `validate`, `start_run`, `cancel_run`, `stream_records`, `list_artifacts`, and `runtime_capabilities`.
- [x] Add `PythonSimulationRuntime` adapter around the current `PersephoneEngine`.
- [x] Add `RuntimeCapability` model: backend name, version, live frame support, replay support, pause/resume support, max recommended frame rate.
- [x] Add `runtime_backend` and `runtime_version` fields to run manifests.
- [x] Keep API and UI responses independent of Python object internals.
- [x] Add tests that existing run execution works through `PythonSimulationRuntime`.
- [x] Add tests that manifests record runtime metadata.
- [x] Document how a future Rust runtime can implement the same interface.
- [ ] Commit: `feat: add engine runtime interface`.

### Checkpoint 1A — Domain-agnostic platform cleanup

This checkpoint makes domain agnosticism an explicit v3 invariant. By the end of v3, Persephone should be able to host arbitrary plugins without core API, CLI, or Studio UI code assuming SIR, heat diffusion, epidemic metrics, temperature fields, or any other specific simulation domain.

- [x] Add a domain-term leak test that scans `src/persephone`, `sdk/src`, and shared UI infrastructure for forbidden domain terms outside allowed paths.
- [x] Allowed paths should include plugin packages, example configs, docs/examples, and plugin-specific tests.
- [x] Remove SIR-specific metric filtering from `persephone replay`; make replay accept `--metric` multiple times or auto-select numeric metrics from the run.
- [x] Remove `infected_count` as the default comparison metric; require `--metric` or choose the first available numeric metric with a clear message.
- [x] Replace `/examples/sir_epidemic` as the only example-oriented API with a generic example catalog:
  - [x] `GET /examples`
  - [x] `GET /examples/{example_id}`
  - [x] include `sir_epidemic` and `heat_diffusion`
- [x] Keep backwards-compatible `/examples/sir_epidemic` only as a deprecated alias during v3 if needed.
- [x] Move field units and visualization hints out of name-based inference in `fields.py`.
- [x] Source field units, palettes, and visualization hints from plugin renderer metadata or frame metadata.
- [ ] Replace MVP UI SIR-specific experiment builder assumptions with plugin-schema-driven form generation.
- [x] Replace MVP UI SIR-specific metric summary cards with schema/capability-driven metric summaries.
- [x] Replace hardcoded sweep defaults such as `solvers[0].params.p_infect` with user-selected schema paths.
- [x] Ensure routes, stores, and components are named by generic concepts: plugin, experiment, run, metric, frame, artifact, inspector.
- [x] Keep SIR and heat as example presets, not platform assumptions.
- [ ] Add tests proving a scaffolded third plugin can appear in plugin catalog, form generation, run creation, metric display, and artifact listing without code changes.
- [x] Add docs: `docs/domain-agnostic-platform.md`.
- [ ] Commit: `refactor: remove domain assumptions from platform core`.

### Checkpoint 2 — Visualization frame contract

- [x] Add typed core models for `SimulationFrame`, `FieldFrame`, `GraphFrame`, `FrameIndex`, and `FramePayloadRef`.
- [x] Add JSON Schema export for frame models.
- [x] Define common frame fields: `run_id`, `frame_id`, `kind`, `t`, `tick`, `solver_id`, `source`, `schema_version`.
- [x] Define `FieldFrame`: field name, shape, dtype, bounds, units, visualization hints, inline values or artifact URL.
- [x] Define `GraphFrame`: nodes, edges, positions, node state, edge weights, visualization hints.
- [x] Add frame validation before storage or streaming.
- [x] Add frame size policy: inline small frames, artifact references for large frames.
- [x] Add tests for valid and invalid frame records.
- [x] Add docs: `docs/frame-contract.md`.
- [ ] Commit: `feat: define simulation frame contract`.

### Checkpoint 3 — Frame emission from plugins and engine

- [x] Extend plugin SDK renderer contract to optionally emit normalized frames.
- [x] Keep renderers storage-agnostic and UI-agnostic.
- [x] Implement `HeatRenderer.frame(...)` returning `FieldFrame`.
- [x] Implement `SIRRenderer.frame(...)` returning `GraphFrame`.
- [x] Add scheduler hook to collect visual frames at configured cadence.
- [x] Add `visualization.emit_every` or equivalent config section.
- [x] Ensure frame emission does not force metric emission cadence.
- [x] Add tests for heat field frame generation.
- [x] Add tests for SIR graph frame generation.
- [x] Add tests that frame cadence is honored.
- [ ] Commit: `feat: emit normalized simulation frames`.

### Checkpoint 4 — Frame storage and replay artifacts

- [x] Add `FrameSink` interface.
- [x] Persist frame index under `runs/<run_id>/frames/index.json`.
- [x] Persist small frame payloads as JSONL or compact JSON.
- [x] Persist large field payloads as NPZ/Zarr-compatible artifacts or references.
- [x] Link frame artifacts from run manifest or artifact index.
- [x] Add replay API that can reconstruct frame timeline after process restart.
- [x] Add CLI commands:
  - [x] `persephone frames list <run>`
  - [x] `persephone frames show <run> <frame_id>`
  - [x] `persephone frames export <run> <frame_id>`
- [x] Add tests for frame index, payload persistence, and replay discovery.
- [ ] Commit: `feat: persist replay frames`.

### Checkpoint 5 — Live frame streaming API

- [x] Add `GET /runs/{run_id}/frames/stream`.
- [x] Stream frames as SSE first.
- [x] Add event names: `frame`, `metric`, `event`, `status`, `error`, `heartbeat`.
- [x] Include monotonic sequence ids for reconnect/resume.
- [x] Add `Last-Event-ID` support or equivalent resume token.
- [x] Add backpressure policy for high-frequency frames.
- [x] Add frame thinning/downsampling policy for UI-safe streaming.
- [x] Add API tests for streaming heat frames while a run is active.
- [x] Add API tests for graceful completion and failure.
- [x] Document when WebSocket should replace or supplement SSE later.
- [ ] Commit: `feat: stream live simulation frames`.

### Checkpoint 6 — Replay frame API

- [x] Add `GET /runs/{run_id}/frames`.
- [x] Add `GET /runs/{run_id}/frames/{frame_id}`.
- [x] Add query options for frame kind, time range, solver id, and max count.
- [x] Add response metadata for available frame kinds and time bounds.
- [x] Add API tests for completed heat diffusion replay frames.
- [x] Add API tests for SIR graph replay frames.
- [x] Add error responses for missing runs, missing frames, and unsupported frame formats.
- [ ] Commit: `feat: add replay frame API`.

### Checkpoint 7 — Hardened OpenAPI and typed client

- [x] Ensure every public route has explicit request and response models.
- [x] Standardize API error model: code, message, details, request id.
- [x] Add OpenAPI snapshot test.
- [x] Add schema compatibility test for critical models.
- [x] Generate TypeScript API client from OpenAPI, or create a strongly typed client package with schema tests.
- [x] Put generated/manual client under `ui/src/lib/api-client/`.
- [x] Replace ad hoc frontend fetch types with the typed client.
- [x] Add tests that frontend client types match API fixtures.
- [ ] Commit: `feat: harden API contracts for Studio UI`.

### Checkpoint 8 — Optional Hono gateway spike

This is a spike, not required for v3 shipping.

- [ ] Create `gateway/` with Bun + Hono if the FastAPI contract feels limiting for the UI.
- [ ] Proxy `/api/*` to FastAPI.
- [ ] Add one UI-shaped aggregate endpoint, such as `/studio/runs/{run_id}`.
- [ ] Test Hono RPC/client typing against one route.
- [ ] Evaluate whether Hono reduces frontend complexity enough to keep.
- [ ] Document decision: keep, defer, or remove.
- [ ] Do not make the UI depend on Hono-only behavior unless the decision is to keep it.
- [ ] Commit if kept: `feat: add Hono Studio gateway`.

### Checkpoint 9 — Studio design system foundation

- [x] Define product design principles: instrument-like, calm, dense, readable, non-technical default, technical on demand.
- [x] Create Studio color tokens with light and dark themes.
- [x] Create typography scale for app shell, panels, charts, dense tables, and viewport overlays.
- [x] Create spacing, radius, elevation, and border tokens.
- [x] Build shadcn-svelte wrapper components for Persephone-specific usage.
- [x] Add icon language with `lucide-svelte`.
- [x] Add design system page or Storybook-like internal route if lightweight.
- [x] Ensure cards are not used as page-section wrappers; use panels, docks, and workbench regions.
- [x] Add accessibility checks for contrast and keyboard navigation.
- [ ] Commit: `feat: add Studio design system foundation`.

### Checkpoint 10 — Studio shell layout

- [x] Replace MVP navigation with Studio shell.
- [x] Add persistent top bar with project/run context and command actions.
- [x] Add left icon rail for Studio, Runs, Sweeps, Compare, Artifacts, Plugins, Settings.
- [x] Add contextual left panel for experiment controls.
- [x] Add central viewport region.
- [x] Add right inspector panel.
- [x] Add bottom analysis dock with tabs for Metrics, Events, Frames, Artifacts, Logs.
- [x] Add resizable/collapsible panels.
- [x] Add responsive fallback for laptop and tablet widths.
- [x] Add Playwright screenshots for key shell states.
- [ ] Commit: `feat: build Simulation Studio shell`.

### Checkpoint 11 — Playback engine store

- [x] Add frontend playback store: mode, status, current time, speed, frame buffer, selected frame, selected object.
- [x] Support live source and replay source with the same interface.
- [x] Add buffering policy for incoming live frames.
- [x] Add pause, resume, scrub, jump-to-start, jump-to-end, speed control.
- [x] Add local pause while backend run continues.
- [x] Add transition from live mode to replay mode after completion.
- [x] Add unit tests for playback state transitions.
- [x] Add UI tests for controls.
- [ ] Commit: `feat: add Studio playback engine`.

### Checkpoint 12 — Canvas viewport renderer

- [x] Add `SimulationViewport.svelte`.
- [x] Add canvas sizing with device-pixel-ratio support.
- [x] Add renderer registry keyed by frame kind.
- [x] Implement `FieldFrameCanvasRenderer`.
- [x] Implement color palettes, autoscale/manual bounds, and opacity controls.
- [x] Implement pointer hover and click selection for field cells.
- [x] Add empty/loading/error viewport states.
- [x] Add canvas pixel tests or Playwright visual smoke checks.
- [x] Add performance guard so Svelte does not rerender on every animation frame.
- [ ] Commit: `feat: render field frames in canvas viewport`.

### Checkpoint 13 — Graph frame renderer

- [x] Implement `GraphFrameCanvasRenderer` or SVG/canvas hybrid renderer.
- [x] Support node state coloring for SIR susceptible/infected/recovered states.
- [x] Support edge weight styling.
- [x] Support static layout first, then optional D3 force layout if needed.
- [x] Add hover/click node inspection.
- [x] Add playback support for infection spread frames.
- [x] Add tests using SIR replay frames.
- [ ] Commit: `feat: render graph simulation frames`.

### Checkpoint 14 — D3 timeline and analytics dock

- [ ] Add D3 metric timeline component.
- [ ] Support multiple metrics on one timeline.
- [ ] Add event markers.
- [ ] Add frame tick markers.
- [ ] Add brush/zoom.
- [ ] Sync selected timeline time to playback store.
- [ ] Add metric cards for current frame and selected time.
- [ ] Add events/logs table.
- [ ] Add tests for timeline interactions.
- [ ] Commit: `feat: add synchronized D3 analysis timeline`.

### Checkpoint 15 — Experiment builder for non-technical users

- [ ] Add plugin selection flow.
- [ ] Render parameter forms from plugin schemas.
- [ ] Add friendly labels, descriptions, units, defaults, and validation messages.
- [ ] Add presets for SIR and heat diffusion examples.
- [ ] Add advanced technical tab for raw YAML/schema view.
- [ ] Add safe validation before run submission.
- [ ] Add run button that opens live playback immediately.
- [ ] Add tests for successful and invalid experiment creation.
- [ ] Commit: `feat: add Studio experiment builder`.

### Checkpoint 16 — Inspector system

- [ ] Add inspector store for selected frame, selected field cell, selected graph node, selected artifact, and selected metric.
- [ ] Add field inspector: value, coordinates, units, bounds, dtype, shape, frame id, source.
- [ ] Add graph node inspector: id, state, degree, event history if available.
- [ ] Add run inspector: status, runtime backend, config hash, plugin versions, seed plan.
- [ ] Add visualization controls: palette, scale, opacity, layer visibility.
- [ ] Add technical details disclosure for advanced users.
- [ ] Add tests for selection and inspector updates.
- [ ] Commit: `feat: add Studio inspector`.

### Checkpoint 17 — Results, artifacts, and exports UX

- [ ] Add artifact browser in the analysis dock.
- [ ] List metrics, events, frames, checkpoints, final state, field artifacts, and exports.
- [ ] Add one-click CSV and Parquet export from the UI.
- [ ] Add field frame export.
- [ ] Add run comparison entry point from current run.
- [ ] Add clear completed/failed/cancelled run states.
- [ ] Add tests for export and artifact interactions.
- [ ] Commit: `feat: add Studio artifact and export workflows`.

### Checkpoint 18 — Sweep and comparison Studio workflows

- [ ] Add sweep builder with scalar path selection.
- [ ] Show sweep child runs as comparable playback entries.
- [ ] Add compare workspace that can overlay metric timelines.
- [ ] Add side-by-side run metadata.
- [ ] Add frame comparison placeholder for future multi-run visual overlays.
- [ ] Add tests for creating and comparing a sweep from the UI.
- [ ] Commit: `feat: add Studio sweep comparison workflows`.

### Checkpoint 19 — Professional polish and accessibility

- [ ] Add command palette.
- [ ] Add keyboard shortcuts for run, pause, scrub, inspector focus, and panel toggles.
- [ ] Add consistent loading skeletons.
- [ ] Add empty states that guide non-technical users without sounding like docs.
- [ ] Add error states with recovery actions.
- [ ] Add app-wide toasts or status notifications.
- [ ] Add focus management for dialogs and panels.
- [ ] Add accessibility checks for controls, charts, and canvas alternatives.
- [ ] Add reduced-motion handling.
- [ ] Commit: `feat: polish Studio interaction model`.

### Checkpoint 20 — Docker and local deployment

- [ ] Update Docker Compose for the Studio UI.
- [ ] Ensure API and UI containers work with frame streaming.
- [ ] Add health checks for API and UI.
- [ ] Add environment variables for API base URL and optional gateway URL.
- [ ] Add docs for local Studio startup.
- [ ] Add Docker smoke tests.
- [ ] Commit: `chore: update Docker stack for Studio`.

### Checkpoint 21 — Documentation

- [ ] Add `docs/studio-ui.md`.
- [ ] Add `docs/frame-streaming.md`.
- [ ] Add `docs/api-contracts.md`.
- [ ] Add `docs/runtime-interface.md`.
- [ ] Add `docs/future-hono-gateway.md`.
- [ ] Add `docs/future-rust-runtime.md`.
- [ ] Update README with Studio quickstart.
- [ ] Add screenshots or rendered UI previews.
- [ ] Commit: `docs: document v3 Studio architecture`.

### Checkpoint 22 — Version 3 quality gate

- [ ] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv sync`.
- [ ] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest --cov=persephone --cov=persephone_sdk`.
- [ ] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv run ruff check .`.
- [ ] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv run ruff format --check .`.
- [ ] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv run mypy src sdk/src plugins/persephone-plugin-sir-epidemic/src plugins/persephone-plugin-heat-diffusion/src`.
- [ ] Run `cd ui && bun run check`.
- [ ] Run `cd ui && bun run lint`.
- [ ] Run `cd ui && bun run test:unit`.
- [ ] Run `cd ui && bun run build`.
- [ ] Run `cd ui && bunx playwright test --project=chromium`.
- [ ] Run heat diffusion live playback smoke test.
- [ ] Run SIR graph replay smoke test.
- [ ] Run frame streaming API smoke test.
- [ ] Run Docker Compose smoke test.
- [ ] Update `docs/release-v0.3.md`.
- [ ] Commit: `test: complete v3 quality gate`.

---

## 6. Version 4 Candidates

These should wait until the Studio UI and frame contracts reveal real needs:

- Hono gateway as production BFF.
- Redis-backed run queue and live stream fanout.
- TimescaleDB metrics store.
- ClickHouse event store.
- Object storage for large frame payloads.
- Rust accelerated kernels.
- Rust runtime backend.
- WASM plugin sandboxing.
- Multi-user auth and projects.
- Kubernetes deployment.
- Distributed worker execution.
- WebGPU renderers.
