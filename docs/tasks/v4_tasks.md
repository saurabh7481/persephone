# Persephone Version 4 Task List

## 1. Version 4 Product Aim

Version 3 made Persephone a usable Simulation Studio: live playback, replay artifacts, typed frame contracts, a Studio shell, experiment creation, and baseline inspection of fields and graph frames.

Version 4 should make Persephone a **domain-flexible simulation analysis platform**:

> A user can run a simulation from any trusted plugin domain, open the run page, immediately understand what is happening in plain language, switch between the views that make sense for that domain, inspect the most important entities and events, and optionally turn on a minimal AI interpretation layer for concise, evidence-backed summaries.

The centerpiece is no longer just playback. It is **interpretable playback**:

- plugins describe the meaning of their entities, states, metrics, events, and recommended views
- the UI adapts to those semantics instead of assuming every dataset is the same
- the optional AI layer explains facts already extracted by deterministic code instead of guessing from raw arrays

## 2. Architecture Direction

Use a four-layer product architecture:

```text
SvelteKit Analysis Studio
  adaptive run page
  reusable standard views
  plugin-aware inspector
  optional AI explanation panels
        |
Typed Studio Contracts
  semantic schemas
  visualization capabilities
  explanation facts
  selected-view preferences
        |
Engine + Plugin Runtime
  deterministic simulation
  semantic adapters
  explanation fact extraction
  replay / live frame emission
        |
Optional Interpretation Layer
  rules-only summarizer
  low-token AI paraphraser
  cached explanations
```

### Simulation stance

Keep the simulation engine deterministic and non-AI. AI must not participate in `World.init()`, `Solver.step()`, scheduler synchronization, or core state mutation.

### AI stance

The AI layer is optional, lightweight, and evidence-backed:

- default mode should be off or rules-only
- minimal AI mode should consume compact fact packets, not raw state tensors
- AI output must be traceable back to metrics, events, entities, and milestone facts

### Plugin stance

Plugins should continue to define simulation behavior, but v4 must add first-class support for:

- semantic metadata
- view capabilities
- explanation fact extraction
- rich node/entity metadata
- domain-specific recommended defaults

### UI stance

The `/runs/{run_id}` page should become the primary analysis surface. Playback, metrics, narrative summaries, and inspection should live in a responsive workbench layout instead of forcing users to scroll past a graph to find meaning.

## 3. Version 4 Acceptance Criteria

- [ ] Core engine, API, and UI remain domain-agnostic and do not hardcode geography, epidemic, stock, or codebase assumptions outside plugins, examples, and tests.
- [ ] Plugins can declare semantic schemas for entities, states, metrics, events, and visualization capabilities.
- [ ] Graph-style frames support richer entity metadata: labels, groups, coordinates, numeric attributes, and extensible view hints.
- [ ] The run page can choose a default visualization based on plugin-declared capabilities instead of always privileging one viewport.
- [ ] The run page supports full-screen playback and full-screen chart analysis.
- [ ] Metrics are readable without scrolling past the viewport and can be pinned, highlighted, or expanded for deeper inspection.
- [ ] The inspector can show human-readable entity details driven by plugin metadata, not only raw ids and counts.
- [ ] Plugins can emit deterministic explanation facts for run-level, frame-level, and selected-entity interpretation.
- [ ] A rules-only explanation layer works without any LLM dependency.
- [ ] An optional minimal AI layer can paraphrase explanation facts into concise summaries with bounded token usage.
- [ ] AI explanations are clearly labeled as interpretation and cite the underlying evidence.
- [ ] Explanation results are cached and replayable so users do not pay token costs repeatedly for the same run/frame/selection.
- [ ] Live runs and replay runs share the same explanation UI surface.
- [ ] At least three distinct plugin domains can be supported by the shared contract without UI rewrites:
  - [ ] spatial/network example
  - [ ] market/system example
  - [ ] codebase/workflow example
- [ ] Docker, CLI, API, and UI quality gates pass.

---

## 4. Version 4 Scope Boundaries

### In scope

- semantic plugin contracts
- richer frame metadata
- deterministic explanation facts
- optional low-token AI interpretation
- run page layout and usability overhaul
- capability-driven view selection
- better graph rendering modes and layout choices
- reusable inspector and explanation components

### Out of scope

- AI-driven state mutation
- unbounded chat over raw run history
- arbitrary LLM calls on every tick
- full natural-language run control
- bespoke custom visualizations for every plugin before standard view primitives are mature
- community/untrusted plugin sandboxing

## 5. Agent Orientation and Execution Rules

This section exists so an implementation agent can read this document with minimal repo context and still work safely.

### 5.1 Primary concepts

- **Simulation layer**: deterministic world initialization and stepping. This is the existing `World`, `Solver`, `Observer`, and `Renderer` contract surface in the SDK.
- **Semantic layer**: plugin-provided metadata describing what the simulation means in human terms: entities, states, metrics, events, view capabilities, and explanation capabilities.
- **Frame layer**: normalized artifacts emitted for playback and replay. These should remain transport-safe and UI-consumable.
- **Explanation facts**: structured, deterministic interpretation records derived from state, metrics, and events before any LLM is involved.
- **Interpretation layer**: optional post-processing that can be rules-only or low-token AI-backed. It must never mutate state or drive simulation decisions.
- **Run page workbench**: the `/runs/[runId]` analysis surface in the Svelte UI. This is the main UX target for v4.

### 5.2 Current file map

These are the primary files and modules an implementation agent should inspect before changing behavior.

#### SDK and engine contracts

- `sdk/src/persephone_sdk/plugin.py`
  - plugin manifest and simulation interface contracts
- `sdk/src/persephone_sdk/types.py`
  - runtime-facing frame and record type aliases
- `src/persephone/core/frames.py`
  - validated normalized frame models used by storage/API
- `src/persephone/core/scheduler.py`
  - frame emission cadence and live run coordination
- `src/persephone/storage/frames.py`
  - replay frame persistence and retrieval
- `src/persephone/registry/registry.py`
  - plugin discovery and manifest loading

#### API surface

- `src/persephone/api/schemas.py`
  - FastAPI response/request models
- `src/persephone/api/manager.py`
  - run orchestration and stream aggregation
- `src/persephone/api/routes/frames.py`
  - replay frame endpoints
- `src/persephone/api/routes/examples.py`
  - example discovery and config hydration

#### UI analysis surface

- `ui/src/routes/runs/[runId]/+page.svelte`
  - current run page layout, playback controls, inspector, dock
- `ui/src/lib/components/studio/SimulationViewport.svelte`
  - viewport shell and per-frame overlays
- `ui/src/lib/studio/renderers.ts`
  - field/graph rendering and graph layout fallback behavior
- `ui/src/lib/studio/inspector.ts`
  - field-cell and graph-node inspection helpers
- `ui/src/lib/api-client/types.ts`
  - UI-side typed API contracts

### 5.3 Existing behavior constraints

An implementation agent must preserve these unless a checkpoint explicitly changes them.

- Existing v3 plugins must continue to run.
- Existing frame payloads must continue to validate.
- Replay and live playback must remain compatible.
- Simulation determinism must not depend on AI availability.
- Docker and local development paths must remain supported together.
- The UI must still work when a plugin does not opt into new semantic or explanation features.

### 5.4 Hard invariants

These are non-negotiable architecture rules for v4.

- AI must never run inside `World.init()`, `Solver.step()`, scheduler time advancement, or any state mutation path.
- AI must consume compact deterministic facts, not arbitrary raw tensors or full event histories by default.
- The semantic and explanation contracts must be domain-agnostic. Do not hardcode county, epidemic, stock, or codebase terms into the platform core.
- The run page must remain usable with no AI configured.
- The UI must present evidence for explanations, not unsupported claims.
- Backward compatibility for v3 plugins is a product requirement, not optional cleanup.

### 5.5 Anti-hallucination rules for implementation agents

- Do not invent new plugin capabilities without first defining typed contracts for them in SDK/API/UI layers.
- Do not add fields to UI code only. Every new cross-layer field must be reflected in:
  - SDK/runtime shape if emitted by plugins
  - engine/API validation layer
  - TypeScript client types
  - tests/fixtures
- Do not let the run page assume every plugin emits graph frames.
- Do not let explanation text become the only source of truth; facts and evidence must remain inspectable.
- Do not silently change existing API response shapes without updating OpenAPI and client types.
- Do not let dense graph rendering regress field playback behavior.

### 5.6 Required workflow for each checkpoint

For every checkpoint:

1. Read the relevant current files listed in section 5.2 before editing.
2. Identify the exact contract boundary being changed.
3. Update tests or fixtures first when practical.
4. Update Python and TypeScript contract types together if the change crosses the API boundary.
5. Run the smallest relevant verification commands immediately after the change.
6. Only then move on to the next checkpoint.

### 5.7 Checkpoint dependency order

The checkpoints are intentionally ordered. Do not skip ahead casually.

- Checkpoint 1 must land before Checkpoints 2, 3, 5, 6, 11, and 13.
- Checkpoint 2 must land before Checkpoints 6, 10, and 11.
- Checkpoint 3 must land before Checkpoints 4, 5, and 12.
- Checkpoint 4 should not start until Checkpoint 3 yields useful non-AI facts.
- Checkpoints 7, 8, 9, 10, 11, and 12 are UI-heavy but depend on the contract work from 1 to 6.
- Checkpoint 13 is the proof that the earlier abstractions are truly domain-agnostic.

### 5.8 Checkpoint-to-file guide

This table is not exhaustive, but it tells an agent where to start.

| Checkpoint | Primary files likely touched |
|---|---|
| 1 | `sdk/src/persephone_sdk/plugin.py`, `sdk/src/persephone_sdk/types.py`, `src/persephone/api/schemas.py`, `ui/src/lib/api-client/types.ts` |
| 2 | `src/persephone/core/frames.py`, `sdk/src/persephone_sdk/types.py`, plugin renderers, `ui/src/lib/api-client/types.ts` |
| 3 | new engine fact models under `src/persephone/`, plugin hooks, storage and tests |
| 4 | config models/loaders, interpretation service module, caching/persistence code, explanation tests |
| 5 | `src/persephone/api/routes/*`, `src/persephone/api/manager.py`, OpenAPI tests, TS client types |
| 6 | `ui/src/lib/studio/*`, run page routing/state, standard view registry modules |
| 7 | `ui/src/routes/runs/[runId]/+page.svelte`, related workbench/panel components, layout CSS |
| 8 | viewport component, chart containers, playback state management, e2e tests |
| 9 | metric presentation components, run page state, comparison/timeline helpers |
| 10 | `ui/src/lib/studio/renderers.ts`, viewport controls, graph interaction helpers |
| 11 | `ui/src/lib/studio/inspector.ts`, run page inspector panel, API types for semantic metadata |
| 12 | explanation panel components, milestone timeline components, API wiring |
| 13 | plugin examples under `plugins/`, example configs, example API tests, UI adaptation tests |
| 14 | `README.md`, `Persephone.md`, docs under `docs/`, SDK usage docs |
| 15 | all changed surfaces plus CI-quality commands |

### 5.9 Verification expectations by layer

- **Python contract changes**: `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest` on targeted SDK/engine/API tests.
- **API shape changes**: OpenAPI contract tests plus TypeScript client type checks.
- **UI rendering changes**: `cd ui && bun run check && bun run test:unit`.
- **Layout and interaction changes**: end-to-end or screenshot coverage for `/runs/[runId]`.
- **Docker-sensitive changes**: rebuild and verify the API/UI containers if plugin discovery or bundled assets changed.

## 6. Detailed Delivery Notes for Implementation Agents

### 6.1 What success looks like for v4

An agent should consider v4 successful only when the system can answer, from the UI:

- What is happening right now?
- Why is it happening?
- Which entities matter most?
- What changed recently?
- Which visualization best fits this plugin domain?

If the output is still “a graph plus numbers,” then the checkpoint sequence is incomplete even if tests pass.

### 6.2 What not to optimize for first

- Do not start by building a large LLM integration.
- Do not start by inventing custom visualization widgets for one plugin domain.
- Do not overfit the run page to county epidemic data.
- Do not split into many bespoke one-off UI components before the standard view model is clear.

### 6.3 Minimum viable semantic support

If time or scope becomes constrained, the minimum meaningful v4 core is:

- semantic plugin manifest
- richer graph/entity metadata
- rules-only explanation facts
- run page layout overhaul
- metric attention/focus behavior
- schema-driven inspector

This delivers most of the user-facing value even if the optional AI layer ships later.

### 6.4 Compatibility expectations

- Existing plugins with no semantic metadata should fall back to generic labels and views.
- Existing graph renderers with only `id` and `state` should still display.
- Existing field plugins should not lose usability because graph tooling became richer.
- Explanation panels should degrade gracefully to “no interpretation available” when a plugin does not implement facts.

## 7. Version 4 Implementation Task List

### Checkpoint 0 — v3 baseline and branch hygiene

- [x] Confirm all intended v3 work is committed or explicitly parked.
- [x] Confirm `git status --short` is clean except known local scratch files.
- [x] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv sync`.
- [x] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest`.
- [x] Run `cd ui && bun run check && bun run lint && bun run test:unit && bun run build`.
- [x] Create v4 branch: `feat/v4-interpretable-studio`.
- [x] Commit: `chore: start v4 planning baseline`.

### Checkpoint 1 — Define semantic contracts

- [x] Extend the SDK contract surface to add plugin-declared semantics:
  - [x] entity schema
  - [x] state schema
  - [x] metric schema
  - [x] event schema
  - [x] visualization capabilities
  - [x] explanation capabilities
- [x] Decide whether these belong directly on `PluginManifest` or in a nested `SemanticManifest`.
- [x] Add typed Python models for:
  - [x] `EntityField`
  - [x] `StateDefinition`
  - [x] `MetricDefinition`
  - [x] `EventDefinition`
  - [x] `ViewCapability`
  - [x] `ExplanationCapability`
- [ ] Document required vs optional fields for each contract.
- [x] Add SDK tests validating plugin semantic manifests.
- [x] Add examples showing how non-spatial plugins can use the same contracts.
- [ ] Commit: `feat: add semantic plugin contracts`.

### Checkpoint 2 — Evolve normalized frame contracts

- [x] Expand `GraphNode` support to explicitly allow:
  - [x] `label`
  - [x] `group`
  - [x] `lat`
  - [x] `lon`
  - [x] `metrics`
  - [x] `attrs`
- [x] Expand `GraphEdge` support to explicitly allow:
  - [x] `kind`
  - [x] `directed`
  - [x] `attrs`
- [x] Add standardized `visualization` hints for graph frames:
  - [x] `layout_hint`
  - [x] `coordinate_system`
  - [x] `preferred_view`
  - [x] `legend`
  - [x] `selection_schema`
  - [x] `density_hint`
- [x] Keep backward compatibility for existing v3 plugins and frames.
- [x] Add validation tests for old and new graph frame shapes.
- [ ] Commit: `feat: enrich normalized graph frame metadata`.

### Checkpoint 3 — Add deterministic explanation fact model

- [x] Add engine-level typed models for explanation facts:
  - [x] `TrendFact`
  - [x] `MilestoneFact`
  - [x] `AnomalyFact`
  - [x] `HotspotFact`
  - [x] `SelectionFact`
- [x] Standardize fields:
  - [x] `kind`
  - [x] `title`
  - [x] `summary`
  - [x] `severity`
  - [x] `evidence`
  - [x] `related_ids`
  - [x] `t`
- [x] Add plugin hooks for producing facts from state, metrics, and events.
- [x] Add a shared rules-only summarizer that can produce basic explanations without LLMs.
- [x] Add storage for fact packets alongside replay artifacts.
- [x] Add tests covering fact extraction and fact persistence.
- [ ] Commit: `feat: add deterministic explanation fact pipeline`.

### Checkpoint 4 — Add optional AI interpretation layer

- [ ] Add new config section, e.g. `interpretation`.
- [ ] Support modes:
  - [ ] `off`
  - [ ] `rules_only`
  - [ ] `minimal_ai`
- [ ] Add budget controls:
  - [ ] `every_n_ticks`
  - [ ] `on_milestone`
  - [ ] `on_complete`
  - [ ] `max_input_facts`
  - [ ] `max_output_tokens`
- [ ] Implement compact prompt packet generation from deterministic facts.
- [ ] Keep prompts small and domain-agnostic.
- [ ] Add cache keys based on:
  - [ ] run id
  - [ ] frame tick
  - [ ] selection id
  - [ ] plugin version
  - [ ] interpretation mode
- [ ] Store prompt inputs and outputs for replay/debugging when enabled.
- [ ] Add explicit output labeling so the UI can distinguish deterministic vs AI-produced summaries.
- [ ] Add tests for:
  - [ ] disabled mode
  - [ ] rules-only mode
  - [ ] cached minimal AI mode
  - [ ] token-budget enforcement
- [ ] Commit: `feat: add optional low-token interpretation layer`.

### Checkpoint 5 — Expose semantic and explanation APIs

- [ ] Add API routes for:
  - [ ] plugin semantic metadata
  - [ ] run explanation summaries
  - [ ] frame explanation summaries
  - [ ] selected-entity explanation summaries
- [ ] Extend run payloads with semantic/view capability references.
- [ ] Add API response models and OpenAPI coverage for all new contracts.
- [ ] Ensure explanation routes work for both completed replay runs and live runs.
- [ ] Add API tests for:
  - [ ] explanation retrieval
  - [ ] explanation cache hits
  - [ ] missing explanation support
  - [ ] disabled AI mode
- [ ] Commit: `feat: expose semantics and explanation APIs`.

### Checkpoint 6 — Build capability-driven standard views

- [ ] Define the standard view registry for v4:
  - [ ] network
  - [ ] positioned graph
  - [ ] map-network
  - [ ] matrix
  - [ ] table
  - [ ] timeline
  - [ ] heatmap
  - [ ] hierarchy
- [ ] Add a view selection layer that chooses defaults from plugin capability metadata.
- [ ] Define per-view requirements and fallbacks:
  - [ ] if coordinates exist, prefer spatial or positioned views
  - [ ] if graph is too dense, prefer matrix or clustered views
  - [ ] if no graph semantics exist, keep charts/tables primary
- [ ] Add tests for capability-driven view selection.
- [ ] Commit: `feat: add capability-driven view registry`.

### Checkpoint 7 — Overhaul `/runs/{run_id}` page information architecture

- [ ] Redesign the run page into a balanced workbench where no critical information is hidden below the fold by default.
- [ ] Promote summary cards, selected metrics, and explanation panels above or beside the main viewport.
- [ ] Add persistent sections for:
  - [ ] run status and playback controls
  - [ ] key metrics at current time
  - [ ] “what’s happening” explanation panel
  - [ ] viewport/view switcher
  - [ ] entity inspector
  - [ ] events and artifacts
- [ ] Ensure the default desktop layout keeps viewport, key metrics, and explanation summary visible together.
- [ ] Ensure laptop and tablet layouts degrade gracefully.
- [ ] Add wireframe screenshots or design references for the intended layout states.
- [ ] Commit: `feat: redesign run analysis workspace`.

### Checkpoint 8 — Full-screen and focus modes

- [ ] Add full-screen mode for the main viewport.
- [ ] Add full-screen mode for metric analysis panels/charts.
- [ ] Preserve playback state and selection when toggling full-screen.
- [ ] Add keyboard shortcuts for:
  - [ ] toggle viewport full-screen
  - [ ] toggle chart full-screen
  - [ ] next/previous frame
  - [ ] play/pause
- [ ] Add tests for full-screen and focus state transitions.
- [ ] Commit: `feat: add analysis full-screen modes`.

### Checkpoint 9 — Metric readability and attention system

- [ ] Replace the current “metrics tucked below the viewport” presentation with a first-class metric deck.
- [ ] Add metric cards that support:
  - [ ] pinned metrics
  - [ ] compact vs expanded states
  - [ ] sparkline or delta context
  - [ ] severity highlighting
  - [ ] threshold markers
  - [ ] current-value emphasis
- [ ] Let plugins or semantic metadata declare recommended “headline metrics”.
- [ ] Add metric attention states:
  - [ ] stable
  - [ ] rising concern
  - [ ] critical
  - [ ] improving
- [ ] Add the ability to focus one metric at a time in a larger chart panel.
- [ ] Add tests for metric ranking, pinning, and attention rendering.
- [ ] Commit: `feat: improve metric readability and attention states`.

### Checkpoint 10 — Rich graph rendering and density handling

- [ ] Improve graph rendering for diverse domains:
  - [ ] stable layout across time
  - [ ] positioned layout support
  - [ ] map/network overlay support
  - [ ] density-aware edge rendering
  - [ ] node sizing by metric
  - [ ] hover labels
  - [ ] search and highlight
- [ ] Add fallbacks for dense graphs:
  - [ ] adjacency matrix mode
  - [ ] community/cluster aggregation
  - [ ] edge threshold filtering
- [ ] Add pan/zoom for graph views.
- [ ] Add tests for layout determinism, hit-testing, and performance-sensitive rendering paths.
- [ ] Commit: `feat: strengthen graph analysis views`.

### Checkpoint 11 — Schema-driven inspector

- [ ] Replace hardcoded graph-node inspection with schema-driven rendering.
- [ ] Display:
  - [ ] human-readable label
  - [ ] state
  - [ ] group/region/category
  - [ ] local metrics
  - [ ] recent events
  - [ ] explanation facts for the selected entity
- [ ] Add support for inspecting edges/relationships, not only nodes.
- [ ] Add support for non-graph entity inspection through tables or hierarchical selections.
- [ ] Add tests for inspector rendering across multiple plugin semantic shapes.
- [ ] Commit: `feat: add schema-driven inspector`.

### Checkpoint 12 — Narrative summaries and milestone timeline

- [ ] Add a “What’s happening” panel driven by deterministic facts or AI-paraphrased summaries.
- [ ] Add a “What changed recently” panel for frame-to-frame deltas.
- [ ] Add a milestone timeline with markers for:
  - [ ] peaks
  - [ ] threshold crossings
  - [ ] anomaly starts/ends
  - [ ] major event bursts
- [ ] Allow clicking a milestone to jump playback to the relevant frame.
- [ ] Add tests for milestone extraction and timeline linking.
- [ ] Commit: `feat: add narrative summaries and milestones`.

### Checkpoint 13 — Cross-domain examples and fixture plugins

- [ ] Keep the county epidemic plugin as one example, but add at least two more semantic fixtures:
  - [ ] a market-style plugin or synthetic sector/correlation example
  - [ ] a codebase/workflow plugin or synthetic dependency-risk example
- [ ] Ensure these examples rely on the same shared contracts and standard views.
- [ ] Add UI and API tests proving the run page adapts across domains without custom page rewrites.
- [ ] Commit: `feat: validate cross-domain semantic contracts`.

### Checkpoint 14 — Documentation and migration guidance

- [ ] Update SDK docs for semantic manifests and explanation hooks.
- [ ] Add migration guidance for existing plugins.
- [ ] Document how to keep AI interpretation low-token and evidence-backed.
- [ ] Document how plugins should choose default views and expose entity labels.
- [ ] Update README and architecture docs for v4 behavior.
- [ ] Commit: `docs: add v4 semantic and interpretation guidance`.

### Checkpoint 15 — Quality gates and release hardening

- [ ] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest`.
- [ ] Run targeted API contract and frame replay tests.
- [ ] Run `cd ui && bun run check && bun run lint && bun run test:unit && bun run build`.
- [ ] Run Playwright or equivalent end-to-end tests for:
  - [ ] run page layout
  - [ ] full-screen viewport
  - [ ] metric focus
  - [ ] explanation panel
  - [ ] inspector behavior
  - [ ] cross-domain view switching
- [ ] Verify Docker builds and serves the v4 UI/API together.
- [ ] Commit: `chore: ship v4 interpretable analysis studio`.

---

## 8. Priority Notes

### Highest-value early wins

If scope must be staged, prioritize these first:

- semantic plugin contracts
- richer graph/entity metadata
- run page layout overhaul
- metric readability and focus states
- rules-only explanation facts

This set already makes Persephone substantially easier to understand without needing the AI layer.

### AI feature ordering

Build the AI layer last, after deterministic semantics and fact extraction exist. If the facts are not already useful without AI, the AI layer will hide weak underlying contracts instead of improving them.

### Backward compatibility

Version 3 plugins should continue to run with:

- minimal frame fallback behavior
- default generic inspector behavior
- no explanation support

v4 should add capabilities, not require every existing plugin to be rewritten immediately.

## 9. Definition of Done

Version 4 is done when:

- plugin authors can describe what their domain means, not only how it simulates
- the run page is readable and useful without scrolling through a pile of unlabeled charts
- the viewport can expand and analysis panels can take focus cleanly
- metrics feel intentional and prioritized instead of buried
- explanations are concise, evidence-backed, and optional
- the same system can support geography, market, and codebase-style domains through shared contracts
- a user can answer “what is happening and why?” from the UI without reading raw JSON or guessing from tangled graphs
