# Persephone Version 5 Task List

## 1. Version 5 Product Aim

Version 4 established the semantic and explanation foundations for simulation analysis, but the current `/runs/{run_id}` experience still behaves like an internal tool in places instead of a polished product.

Version 5 should focus **only** on the UI and representation layer:

> A user can open any run, immediately understand the story of the simulation, read the most important numbers without friction, switch views without confusion, and use the experience comfortably across laptop, desktop, and tablet sizes with no overflow-driven layout failures.

The core v5 job is not new simulation capability. It is **presentation quality**:

- responsive layout without panel collisions or horizontal overflow
- first-class light and dark themes
- user-friendly narrative first, technical detail second
- readable numbers and labels everywhere
- view surfaces that feel intentional instead of loosely assembled
- consistent interaction, spacing, density, and fallback behavior

Version 5 must also absorb the deferred **Checkpoint 6B** work from v4 so the standard views feel complete rather than partially stubbed.

## 2. Version 5 Scope Boundaries

### In scope

- run page information architecture refinement
- responsive behavior across desktop, laptop, and tablet breakpoints
- dark mode and theme-system polish for the analysis workspace
- number formatting and metric presentation rules
- narrative-first explanation hierarchy
- schema-aware but user-friendly inspector presentation
- richer standard view implementations from v4 Checkpoint 6B
- consistent empty, loading, overflow, truncation, and fallback states
- accessibility and keyboard-flow polish for analysis surfaces
- visual density, spacing, wrapping, and interaction cleanup
- UI tests, screenshot coverage, and layout regression protection

### Out of scope

- new simulation engine features
- new semantic contract families unless UI polish absolutely requires a small additive field
- large new AI features
- plugin-domain-specific bespoke dashboards
- replacing the v4 explanation pipeline
- backend refactors that do not directly improve presentation quality

## 3. Version 5 Product Principles

### 3.1 Narrative first

The first thing a user should see is the answer to:

- What is happening?
- Is it good, bad, or neutral?
- Why does it matter?
- What should I look at next?

Raw ids, internal metric keys, and dense fact lists should support that story, not lead it.

### 3.2 Technical detail on demand

Technical detail is valuable, but it must move behind expansion, drill-in, or secondary panels:

- human labels before raw metric ids
- interpretation summary before evidence list
- concise values before full precision
- status meaning before schema vocabulary

### 3.3 Layout must not fight the user

The run page must remain readable at common viewport sizes without:

- horizontal page overflow
- clipped cards
- metric labels crashing into values
- panels forcing users to hunt for the main explanation
- full-screen modes breaking surrounding layout state

### 3.4 Representation should be deterministic and consistent

The same value, severity, label, and entity meaning should render consistently across cards, charts, inspector panels, tooltips, tables, and explanation surfaces.

### 3.5 Dark mode is part of the product, not a skin

Dark mode should feel intentionally designed for analysis work:

- contrast must stay readable for charts, cards, controls, and inspector content
- emphasis states must remain clear without neon noise or muddy surfaces
- the visual hierarchy must match light mode rather than becoming a degraded variant
- theme switching should preserve usability, not just invert colors

## 4. Version 5 Acceptance Criteria

- [ ] No critical `/runs/{run_id}` layout overflows remain at supported desktop, laptop, and tablet widths.
- [ ] The run page supports a polished dark mode as a first-class theme, not an afterthought.
- [ ] The default run page clearly prioritizes user-facing summary over technical detail.
- [ ] Raw metric ids are never the primary headline when a human-readable semantic label exists.
- [ ] Numeric values use consistent formatting rules:
  - [ ] compact large-number formatting where appropriate
  - [ ] bounded decimal precision
  - [ ] unit-aware rendering
  - [ ] consistent percent, delta, and threshold formatting
- [ ] Metric cards never allow long values to visually collide, overlap, or escape their containers.
- [ ] Explanation panels present a plain-language primary summary before evidence chips, ids, or technical packets.
- [ ] View switching is understandable and each standard view has a clear purpose, fallback, and empty state.
- [ ] The deferred v4 richer standard views are implemented and integrated into the shared registry:
  - [ ] positioned graph
  - [ ] map-network
  - [ ] adjacency matrix
  - [ ] hierarchy
  - [ ] richer table inspection mode
  - [ ] polished timeline and heatmap switching
- [ ] Inspector content is legible and progressively disclosed, not a raw dump.
- [ ] Light and dark themes both preserve readable contrast for metrics, charts, explanation cards, chips, controls, and inspector content.
- [ ] Keyboard shortcuts, focus modes, and full-screen states remain usable after the layout cleanup.
- [ ] The experience is validated by responsive UI coverage, not only unit tests.
- [ ] Docker, local dev, and example runs still render correctly after the UI refactor.

## 5. Current UX Problems To Eliminate

These are not abstract goals. Version 5 exists specifically to remove these issues:

- sections overflow across the screen and break layout confidence
- metric values show excessive decimal precision and become hard to scan
- the UI surfaces too much technical structure too early
- multiple panels compete for attention instead of supporting one reading flow
- standard views feel uneven in completeness and polish
- dense metric and explanation surfaces read like developer instrumentation instead of product analysis
- the current experience does not yet guarantee a polished dark-mode reading experience

## 6. Agent Orientation And Working Rules

### 6.1 Primary target surface

The primary target remains:

- `ui/src/routes/runs/[runId]/+page.svelte`

But v5 should assume the real work spans the supporting studio layer rather than only one route file.

### 6.2 Current UI file map

Implementation agents should inspect these first:

- `ui/src/routes/runs/[runId]/+page.svelte`
  - current run-page orchestration, panel ordering, explanation placement, focus state
- `ui/src/lib/components/studio/StudioWorkbench.svelte`
  - overall workbench shell, panel visibility, responsive grid behavior
- `ui/src/lib/components/studio/StudioPanel.svelte`
  - panel framing and header/body structure
- `ui/src/lib/components/studio/SimulationViewport.svelte`
  - view-specific controls, viewport affordances, graph pan/zoom, fallback behavior
- `ui/src/lib/components/studio/MetricDeck.svelte`
  - metric card layout, formatting, density, expansion, full-screen entry points
- `ui/src/lib/studio/tokens.ts`
  - shared studio tokens and a likely entry point for theme consistency work
- `ui/src/lib/components/MetricTimeline.svelte`
  - focused metric chart readability and annotation behavior
- `ui/src/lib/studio/metrics.ts`
  - metric ranking and deck shaping; likely home for presentation metadata
- `ui/src/lib/studio/narrative.ts`
  - summary and recent-change shaping before rendering
- `ui/src/lib/studio/views.ts`
  - standard view registry and view descriptions
- `ui/src/lib/studio/inspector.ts`
  - transformation of selected entities into readable inspection sections
- `ui/src/lib/studio/renderers.ts`
  - view-level rendering options, density handling, hit testing, labels
- `ui/src/lib/studio/run-focus.ts`
  - focus/full-screen state behavior
- `ui/src/lib/api-client/types.ts`
  - client contract shapes that may expose semantic labels, units, and view metadata

### 6.3 Strong v5 constraints

- Do not treat responsive polish as “follow-up cleanup.” It is the main feature.
- Do not solve crowded UI by exposing more panels by default.
- Do not expose raw backend naming when semantic labels are available.
- Do not let long numbers dictate card width or destroy alignment.
- Do not hide core understanding behind expansions while leaving technical fragments visible by default.
- Do not add domain-specific wording into shared UI components.
- Do not regress live playback, replay playback, or full-screen analysis behavior while improving layout.
- Do not ship dark mode as a low-contrast inversion that weakens chart and status readability.

## 7. Representation Rules For Version 5

### 7.1 Number formatting rules

- Headline values should usually render with 0 to 2 decimals.
- Secondary values may use up to 3 decimals only when precision materially changes meaning.
- Very large values should use compact separators or suffixes where appropriate.
- Deltas should render with concise signs and bounded percentage precision.
- Thresholds should use the same formatter as headline values.
- Tooltips or drill-in surfaces may expose fuller precision if needed.
- The same metric should not appear as `21.35764360131670` in one place and `21.36` in another unless one surface explicitly indicates detailed precision.

### 7.2 Labeling rules

- Prefer semantic display labels over ids.
- Convert machine-style keys into readable labels when no display label exists.
- Keep units visible but visually secondary to the number.
- Status labels should communicate meaning, not only schema vocabulary.

### 7.3 Narrative rules

- Every explanation section should lead with one plain-language sentence.
- Evidence, facts, raw ids, and related metrics should appear after the primary statement.
- “What changed recently” should summarize significance, not only list facts.
- Selected-entity narratives should explain why the entity matters now, not only repeat its state.

### 7.4 Density rules

- Cards should wrap safely before truncating, and truncate safely before overflowing.
- Lists should not become walls of text by default.
- Expand/collapse should reveal more detail without shifting the whole page unpredictably.
- Grid layouts should degrade cleanly as width narrows.

### 7.5 Theme rules

- Light and dark modes should share the same visual hierarchy and interaction model.
- Semantic tones for healthy, warning, critical, selected, and focused states must remain distinguishable in both themes.
- Charts, sparklines, and overlays must be legible in both themes without requiring separate mental parsing.
- Surfaces should feel cohesive across the workbench instead of mixing unrelated neutral scales.

## 8. Version 5 Implementation Task List

### Checkpoint 0 — Capture the broken baseline

- [ ] Capture current desktop, laptop, and tablet screenshots for the main run page states:
  - [ ] hierarchy view
  - [ ] timeline view
  - [ ] metric focus state
  - [ ] viewport full-screen state
  - [ ] explanation-heavy state
- [x] Capture the same baseline states in both light and dark themes once theme support lands, or record missing coverage as an explicit gap.
- [ ] Record specific overflow, wrapping, and hierarchy failures directly in the task notes or test fixtures.
- [x] Identify the smallest set of example runs that reliably reproduce the current UI problems.
- [x] Add or update visual regression targets so v5 has a measurable baseline.
- [ ] Commit: `test: capture v4 run-page UI baseline`

### Checkpoint 1 — Establish responsive layout invariants

- [x] Refactor the run workbench shell so panel regions obey explicit layout invariants at supported widths.
- [ ] Define supported breakpoint behaviors for:
  - [ ] wide desktop
  - [ ] laptop
  - [ ] tablet
- [ ] Define theme invariants for both light and dark mode:
  - [ ] surface hierarchy
  - [ ] text contrast
  - [ ] chart readability
  - [ ] status/severity color clarity
- [x] Prevent page-level horizontal overflow in default states.
- [x] Ensure cards, charts, and side panels can shrink without content escaping.
- [ ] Make panel collapse and visibility controls feel intentional rather than purely technical.
- [x] Add layout tests or screenshot coverage for each breakpoint.
- [ ] Commit: `feat: harden run-page responsive layout`

### Checkpoint 1B — Add first-class dark mode to the analysis workspace

- [x] Add a theme approach for the run-analysis workspace that supports light and dark mode cleanly.
- [x] Ensure all major studio surfaces inherit the same theme system:
  - [x] workbench shell
  - [x] panel chrome
  - [x] metric cards
  - [x] explanation cards
  - [x] viewport controls
  - [x] inspector sections
  - [x] tables, chips, and badges
- [ ] Re-tune chart, sparkline, and overlay colors for dark mode readability.
- [x] Validate contrast and state meaning for healthy, warning, critical, selected, and focused states in both themes.
- [x] Add screenshot or visual regression coverage for both themes.
- [ ] Commit: `feat: add dark mode to analysis workspace`

### Checkpoint 2 — Introduce a shared presentation formatting layer

- [x] Add a shared UI formatting utility for:
  - [x] headline values
  - [x] secondary values
  - [x] deltas
  - [x] percentages
  - [x] thresholds
  - [x] time labels
- [x] Route metric deck, inspector values, explanation snippets, and chart annotations through the shared formatter.
- [x] Add semantic label helpers so machine keys are consistently humanized when explicit display metadata is missing.
- [x] Add tests covering number precision, unit rendering, negative deltas, and large values.
- [ ] Commit: `feat: unify analysis formatting rules`

### Checkpoint 3 — Rebuild the run page reading flow around narrative first

- [x] Re-order the default experience so the page answers “what is happening” before surfacing deep technical structure.
- [x] Reduce initial cognitive load by keeping core summary, key metrics, and active view context tightly grouped.
- [x] Move evidence chips, raw fact references, and technical identifiers into secondary positions.
- [x] Ensure the selected view description helps a user understand why that view is being shown.
- [x] Add responsive behavior so the reading order remains clear when columns stack.
- [ ] Commit: `feat: make run analysis narrative-first`

### Checkpoint 4 — Redesign metric cards for readability under real data

- [x] Refine metric card layout so long labels, units, and values remain readable together.
- [x] Prevent large numbers from overflowing or colliding in compact cards.
- [x] Standardize compact, expanded, pinned, and focused metric states.
- [x] Improve sparkline and delta placement so the current value remains the visual anchor.
- [x] Ensure severity and headline badges help prioritization instead of creating clutter.
- [x] Add tests and screenshots for long labels, large values, many pinned metrics, and narrow widths.
- [ ] Commit: `feat: improve metric card readability`

### Checkpoint 5 — Complete v4 Checkpoint 6B richer standard views

- [x] Add production-ready implementations or polish passes for the deferred shared views:
  - [x] positioned graph
  - [x] map-network
  - [x] adjacency matrix
  - [x] hierarchy
  - [x] richer table inspection mode
  - [x] polished timeline/heatmap switching
- [x] For each view, define:
  - [x] purpose
  - [x] best-fit data conditions
  - [x] fallback behavior
  - [x] empty state
  - [x] loading state
- [x] Add per-view interaction affordances where applicable:
  - [x] legends
  - [x] density controls
  - [x] coordinate-aware overlays
  - [x] selection affordances
  - [x] view-specific help copy
- [x] Keep all richer views connected to the shared capability-driven registry rather than bespoke route logic.
- [x] Add focused UI tests for each standard view surface.
- [ ] Commit: `feat: complete richer standard analysis views`

### Checkpoint 6 — Simplify and humanize inspector presentation

- [x] Rework inspector sections so the top of the panel explains the selected entity in plain language.
- [x] Group schema-driven details into readable subsections rather than raw field dumps.
- [x] Show the most decision-relevant facts first:
  - [x] current state
  - [x] why this entity matters
  - [x] local metrics
  - [x] recent related events
  - [x] linked explanation facts
- [x] De-emphasize raw ids, degrees, and structural metadata unless they help interpretation.
- [x] Add graceful handling for sparse entities, edges, and non-graph selections.
- [ ] Commit: `feat: humanize analysis inspector`

### Checkpoint 7 — Polish explanation and recent-change surfaces

- [x] Rewrite explanation panel rendering so each card has a clear primary statement, supporting detail, and evidence footer.
- [x] Distinguish deterministic fact output from optional AI interpretation without making the panel feel technical by default.
- [x] Improve “What changed recently” so changes read as meaningful deltas, not loose event snippets.
- [x] Make milestone cards scan cleanly at a glance and wrap safely across widths.
- [x] Ensure clicking milestones and related chips still integrates cleanly with playback.
- [ ] Commit: `feat: polish explanation and change surfaces`

### Checkpoint 8 — Tighten viewport controls and view-specific polish

- [x] Reduce control clutter inside the viewport surface.
- [x] Make view-specific controls appear only when relevant.
- [x] Improve graph-specific affordances for search, density filtering, pan/zoom reset, and overlays.
- [x] Ensure field, graph, matrix, and hierarchy states each have clear empty and unsupported messages.
- [x] Preserve usability when the viewport is narrower or embedded beside heavy inspector content.
- [ ] Commit: `feat: refine viewport interaction surfaces`

### Checkpoint 9 — Accessibility and keyboard-flow refinement

- [x] Audit tab order, focus visibility, and keyboard behavior across the workbench.
- [x] Ensure interactive cards, view switchers, and drill-in controls expose clear labels and states.
- [x] Re-check full-screen and focus modes after the layout refactor.
- [x] Improve screen-reader clarity for summary, metrics, and explanation sections where possible.
- [ ] Commit: `feat: improve analysis workspace accessibility`

### Checkpoint 10 — End-to-end responsive QA and release hardening

- [x] Run `cd ui && bun run check && bun run lint && bun run test:unit && bun run build`.
- [x] Run Playwright or equivalent responsive checks covering:
  - [x] no horizontal overflow at supported widths
  - [x] metric card readability
  - [x] explanation-first reading flow
  - [x] view switching across richer standard views
  - [x] inspector readability
  - [x] full-screen/focus state persistence
- [x] Verify both light and dark themes across the same responsive coverage set.
- [x] Verify the example runs from the v4 cross-domain fixtures still render correctly in the v5 UI.
- [x] Re-verify Docker-served UI behavior for the run page.
- [ ] Commit: `chore: harden v5 analysis presentation`

## 9. Priority Notes

### Highest-value first

If v5 must be staged, do this order first:

- responsive layout invariants
- dark mode theme system
- shared number and label formatting
- narrative-first page hierarchy
- metric card readability
- richer standard views from v4 Checkpoint 6B

If these are done well, Persephone will already feel significantly more product-ready.

### What not to mistake for success

Version 5 is **not** successful if:

- the same information is merely restyled while remaining hard to read
- the layout looks better only on a large desktop monitor
- dark mode exists but feels like a quick inversion instead of a designed analysis experience
- raw ids and full-precision floats still dominate the page
- the UI still feels like separate panels competing for attention
- richer views technically exist but still feel unfinished or fallback-heavy

## 10. Definition Of Done

Version 5 is done when:

- the run page feels clean, stable, and intentional at supported sizes
- a non-technical user can understand the main story before seeing implementation detail
- values are formatted consistently and readably across the product
- light and dark themes both feel intentional and readable
- metrics, explanation, viewport, and inspector feel like one coherent analysis experience
- the richer standard views from deferred v4 work are complete enough to trust in real usage
- the UI no longer overflows, collides, or reads like an internal prototype
