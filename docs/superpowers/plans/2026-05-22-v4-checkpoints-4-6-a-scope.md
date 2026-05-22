# V4 Checkpoints 4-6 A-Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the optional interpretation layer, expose semantics and explanation APIs, and introduce capability-driven view selection without attempting the full multi-view UI buildout yet.

**Architecture:** Keep deterministic fact extraction as the source of truth, then layer a small interpretation service on top that can operate in `off`, `rules_only`, or cached `minimal_ai` mode. Surface those results through typed API routes and feed a lightweight frontend view registry that selects the best existing analysis view from plugin semantics and frame metadata.

**Tech Stack:** Python, FastAPI, Pydantic, SvelteKit, TypeScript, Vitest, pytest

---

### Task 1: Add interpretation config and service contracts

**Files:**
- Modify: `src/persephone/config/models.py`
- Modify: `src/persephone/api/schemas.py`
- Modify: `ui/src/lib/api-client/types.ts`
- Create: `tests/core/test_interpretation.py`

- [ ] Write failing tests for interpretation config validation and response labeling.
- [ ] Run the new interpretation tests to verify the config/models are missing.
- [ ] Add typed interpretation config models and cross-layer API/TS shapes.
- [ ] Re-run the interpretation tests until they pass.

### Task 2: Implement cached interpretation service

**Files:**
- Create: `src/persephone/core/interpretation.py`
- Modify: `src/persephone/storage/artifacts.py`
- Modify: `src/persephone/api/manager.py`
- Modify: `tests/core/test_interpretation.py`

- [ ] Add failing tests for `off`, `rules_only`, cached `minimal_ai`, and budget enforcement.
- [ ] Run the targeted test file and confirm failures are caused by missing service behavior.
- [ ] Implement compact prompt-packet generation, cache keys, persisted prompt/output records, and rules-only/minimal-AI execution paths.
- [ ] Re-run the targeted interpretation tests until green.

### Task 3: Expose semantics and explanation APIs

**Files:**
- Modify: `src/persephone/api/routes/plugins.py`
- Modify: `src/persephone/api/routes/runs.py`
- Modify: `src/persephone/api/app.py`
- Modify: `src/persephone/api/schemas.py`
- Modify: `src/persephone/api/manager.py`
- Modify: `ui/src/lib/api-client/client.ts`
- Modify: `ui/src/lib/api-client/types.ts`
- Modify: `tests/api/test_app.py`
- Modify: `tests/api/test_openapi_contracts.py`

- [ ] Add failing API tests for plugin semantics, run/frame/selection explanations, cache hits, and disabled interpretation mode behavior.
- [ ] Run the targeted API tests and confirm the new routes are missing.
- [ ] Implement typed routes, manager helpers, OpenAPI models, and client methods.
- [ ] Re-run the targeted API tests until green.

### Task 4: Add capability-driven standard view selection

**Files:**
- Create: `ui/src/lib/studio/views.ts`
- Create: `ui/src/lib/studio/views.test.ts`
- Modify: `ui/src/routes/runs/[runId]/+page.svelte`
- Modify: `ui/src/lib/components/studio/SimulationViewport.svelte`
- Modify: `ui/src/lib/studio/renderers.test.ts`

- [ ] Add failing frontend tests for view registry coverage, default selection from semantics, and graph/frame fallbacks.
- [ ] Run the targeted Vitest files and confirm the selection logic does not exist yet.
- [ ] Implement the registry, recommendation logic, and minimal run-page integration around the current viewport/timeline/table surfaces.
- [ ] Re-run the targeted frontend tests until green.

### Task 5: Verify the integrated slice

**Files:**
- Modify only if verification reveals breakage in touched files above.

- [ ] Run `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest tests/core/test_interpretation.py tests/api/test_app.py tests/api/test_openapi_contracts.py tests/core/test_explanations.py`
- [ ] Run `cd ui && bun run test:unit -- views renderers api-client`
- [ ] Run `cd ui && bun run check`
- [ ] If all checks pass, summarize the completed A-scope and note that full B-scope view implementations remain for a later checkpoint.
