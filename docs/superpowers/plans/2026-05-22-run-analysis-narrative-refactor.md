# Run Analysis Narrative Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the `/runs/[runId]` page into a narrative-first analysis page that is simple by default, optimized for completed runs, and progressively reveals technical detail only when the user asks for it.

**Architecture:** Keep the existing data sources and plugin-aware view selection, but add a shared run-page presentation model that decides what the user should see first, what should be hidden, and when secondary sections should appear. Recompose the route around three primary surfaces: `summary`, `primary visualization`, and `primary metric analysis`, then move explanation, milestones, inspector, artifacts, logs, and manifest into progressive secondary surfaces with plugin-aware empty-state suppression.

**Tech Stack:** SvelteKit, Svelte 5, TypeScript, Tailwind CSS, Vitest, Playwright

---

## Planned File Structure

**New files**

- `ui/src/lib/studio/run-page.ts`
  - Shared presentation model for the run page.
  - Builds the top-line summary, default visible sections, and secondary detail availability from the current run, plugin semantics, explanation cards, metrics, recent changes, and selection state.
- `ui/src/lib/studio/run-page.test.ts`
  - Unit tests for completed-run-first defaults, progressive disclosure rules, and suppression of empty technical/fallback sections.
- `ui/src/lib/components/studio/RunSummaryHero.svelte`
  - Renders the top-of-page analysis shell: verdict, why it matters, next step, current frame, and compact state badges.
- `ui/src/lib/components/studio/RunSecondaryTabs.svelte`
  - Renders the secondary analysis surfaces (`Explain`, `Inspect`, `Timeline`, `Artifacts`, `Debug`) and hides tabs that have no meaningful content.

**Modified files**

- `ui/src/routes/runs/[runId]/+page.svelte`
  - Stop rendering every major panel as a peer.
  - Build the shared presentation model and render the new summary shell + primary view + primary metric + progressive secondary tabs.
- `ui/src/lib/components/studio/index.ts`
  - Export new studio components.
- `ui/src/lib/studio/narrative.ts`
  - Add helpers for concise verdict/meaning/next-step shaping and stricter filtering of low-signal “recent change” items.
- `ui/src/lib/studio/narrative.test.ts`
  - Cover the new summary heuristics and the suppression of scheduler-only summaries when domain-level meaning exists.
- `ui/src/lib/studio/views.ts`
  - Add optional short copy for “why this view now” and “when to open details” in the analysis shell.
- `ui/src/lib/studio/inspector.ts`
  - Add compact inspector-preview shaping so the default page shows a useful empty/selected summary instead of the full inspector by default.
- `ui/src/lib/studio/inspector.test.ts`
  - Cover compact preview shaping.
- `ui/src/routes/app.e2e.ts`
  - Replace “everything visible” assumptions with narrative-first assertions and progressive-detail interaction coverage.
- `ui/src/routes/app.e2e.ts-snapshots/*`
  - Refresh run-page visual baselines after the layout changes.

**Out-of-scope for this slice**

- Python/plugin changes in `plugins/` or `src/persephone/`.
- New explanation facts for plugins that do not emit them yet.
- A separate dedicated debug route.

---

### Task 1: Add a shared run-page presentation model

**Files:**
- Create: `ui/src/lib/studio/run-page.ts`
- Create: `ui/src/lib/studio/run-page.test.ts`
- Modify: `ui/src/lib/studio/narrative.ts`
- Modify: `ui/src/lib/studio/narrative.test.ts`

- [ ] **Step 1: Write the failing presentation-model test**

```ts
import { describe, expect, test } from 'vitest';

import { buildRunPageModel } from './run-page';

describe('buildRunPageModel', () => {
	test('prioritizes completed-run summary, primary visualization, and primary metric', () => {
		const model = buildRunPageModel({
			runStatus: 'completed',
			currentView: {
				label: 'Hierarchy',
				kind: 'hierarchy',
				surface: 'table',
				purpose: 'Organize grouped entities into a readable hierarchy.'
			},
			narrativeLead: {
				eyebrow: 'What is happening now',
				title: 'Pricing service is the current blocker hotspot',
				summary: 'Risk reached 0.37 while backlog climbed to 5.3 review items.',
				significance: 'The strongest recent shift is Pricing service pressure on the critical path.',
				nextStep: 'Use Hierarchy to inspect Pricing service and connected relationships.'
			},
			focusedMetric: {
				metric: 'delivery_risk_index',
				label: 'Delivery risk index',
				headline: true,
				unit: 'idx',
				current: { t: 1, value: 31.53 }
			},
			explanationCards: [],
			recentChanges: [],
			inspectorKind: 'empty',
			hasSelection: false,
			pluginSupportsExplanation: true
		});

		expect(model.primarySections).toEqual(['summary', 'view', 'metric']);
		expect(model.secondaryTabs).toEqual(['inspect', 'artifacts', 'debug']);
		expect(model.summary.title).toBe('Pricing service is the current blocker hotspot');
	});
});
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx vitest run src/lib/studio/run-page.test.ts src/lib/studio/narrative.test.ts
```

Expected:

```text
FAIL  src/lib/studio/run-page.test.ts
Error: Cannot find module '$lib/studio/run-page'
```

- [ ] **Step 3: Add the run-page presentation model and summary filtering**

```ts
// ui/src/lib/studio/run-page.ts
export type RunPageModel = {
	summary: {
		title: string;
		summary: string;
		significance: string;
		nextStep: string;
		status: string;
		viewLabel: string;
		currentFrame: string | null;
	};
	primarySections: Array<'summary' | 'view' | 'metric'>;
	secondaryTabs: Array<'explain' | 'inspect' | 'timeline' | 'artifacts' | 'debug'>;
	showExplainTab: boolean;
	showInspectorPreview: boolean;
	showRecentChanges: boolean;
	showDebugTab: boolean;
};

export function buildRunPageModel(input: {
	runStatus: string;
	currentView: { label: string; kind: string; surface: string; purpose: string };
	narrativeLead: {
		title: string;
		summary: string;
		significance: string;
		nextStep: string;
	};
	focusedMetric: { metric: string; label: string; unit?: string | null; current: { t: number; value: number } } | null;
	explanationCards: Array<{ sourceLabel: string; primaryStatement: string; supportingDetail: string }>;
	recentChanges: Array<{ label: string; summary: string }>;
	inspectorKind: 'empty' | 'field-cell' | 'graph-node' | 'graph-edge';
	hasSelection: boolean;
	pluginSupportsExplanation: boolean;
	currentFrameId?: string | null;
}): RunPageModel {
	const meaningfulExplain = input.pluginSupportsExplanation && input.explanationCards.some((card) => card.sourceLabel !== 'Unavailable');
	const meaningfulRecentChanges = input.recentChanges.some((item) => !item.label.toLowerCase().startsWith('scheduler '));

	const secondaryTabs: RunPageModel['secondaryTabs'] = [];
	if (meaningfulExplain) secondaryTabs.push('explain');
	if (input.hasSelection || input.inspectorKind !== 'empty') secondaryTabs.push('inspect');
	if (meaningfulRecentChanges || input.currentView.surface === 'metrics') secondaryTabs.push('timeline');
	secondaryTabs.push('artifacts', 'debug');

	return {
		summary: {
			title: input.narrativeLead.title,
			summary: input.narrativeLead.summary,
			significance: input.narrativeLead.significance,
			nextStep: input.narrativeLead.nextStep,
			status: input.runStatus,
			viewLabel: input.currentView.label,
			currentFrame: input.currentFrameId ?? null
		},
		primarySections: ['summary', 'view', 'metric'],
		secondaryTabs,
		showExplainTab: meaningfulExplain,
		showInspectorPreview: input.hasSelection,
		showRecentChanges: meaningfulRecentChanges,
		showDebugTab: true
	};
}
```

```ts
// ui/src/lib/studio/narrative.ts
export function isInfrastructureOnlyRecentChange(label: string): boolean {
	return label.toLowerCase().startsWith('scheduler ');
}
```

- [ ] **Step 4: Re-run the targeted tests to verify they pass**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx vitest run src/lib/studio/run-page.test.ts src/lib/studio/narrative.test.ts
```

Expected:

```text
✓ src/lib/studio/run-page.test.ts
✓ src/lib/studio/narrative.test.ts
```

- [ ] **Step 5: Commit**

```bash
cd /Users/saurabh/Projects/Persephone
git add ui/src/lib/studio/run-page.ts ui/src/lib/studio/run-page.test.ts ui/src/lib/studio/narrative.ts ui/src/lib/studio/narrative.test.ts
git commit -m "feat: add run-page presentation model"
```

### Task 2: Extract the top-of-page narrative shell

**Files:**
- Create: `ui/src/lib/components/studio/RunSummaryHero.svelte`
- Modify: `ui/src/lib/components/studio/index.ts`
- Modify: `ui/src/routes/runs/[runId]/+page.svelte`
- Test: `ui/src/routes/app.e2e.ts`

- [ ] **Step 1: Write the failing browser test for the first screen**

```ts
test('shows a summary-first completed-run shell before deep analysis panels', async ({ page }) => {
	await page.goto('/runs/run-workflow');
	await pausePlaybackIfNeeded(page);

	await expect(page.getByRole('heading', { name: 'Pricing service is the current blocker hotspot' })).toBeVisible();
	await expect(page.getByText('Why it matters')).toBeVisible();
	await expect(page.getByText('What to inspect next')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Viewport' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Explanation detail' })).toHaveCount(0);
});
```

- [ ] **Step 2: Run the targeted browser test to verify it fails**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx playwright test -g "shows a summary-first completed-run shell before deep analysis panels"
```

Expected:

```text
Error: expected "Explanation detail" to have count 0, received 1
```

- [ ] **Step 3: Add the reusable summary hero component and wire it into the route**

```svelte
<!-- ui/src/lib/components/studio/RunSummaryHero.svelte -->
<script lang="ts">
	let {
		status,
		viewLabel,
		title,
		summary,
		significance,
		nextStep,
		currentFrame,
		metricLabel,
		metricValue
	}: {
		status: string;
		viewLabel: string;
		title: string;
		summary: string;
		significance: string;
		nextStep: string;
		currentFrame: string | null;
		metricLabel: string;
		metricValue: string;
	} = $props();
</script>

<div class="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(18rem,0.9fr)]">
	<div class="space-y-3">
		<div class="flex flex-wrap gap-2 text-xs text-muted-foreground">
			<span class="rounded-full border px-2 py-1">{status}</span>
			<span class="rounded-full border px-2 py-1">{viewLabel}</span>
			{#if currentFrame}
				<span class="rounded-full border px-2 py-1">{currentFrame}</span>
			{/if}
		</div>
		<h2 class="text-2xl font-semibold tracking-tight text-balance">{title}</h2>
		<p class="max-w-3xl text-sm leading-6 text-muted-foreground">{summary}</p>
	</div>
	<div class="grid gap-3">
		<div class="rounded-xl border bg-background/70 p-3">
			<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Why it matters</p>
			<p class="mt-2 text-sm leading-6">{significance}</p>
		</div>
		<div class="rounded-xl border bg-background/70 p-3">
			<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">What to inspect next</p>
			<p class="mt-2 text-sm leading-6">{nextStep}</p>
		</div>
		<div class="rounded-xl border bg-muted/25 p-3">
			<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Primary metric</p>
			<p class="mt-2 text-sm font-semibold">{metricLabel}</p>
			<p class="mt-1 text-xs text-muted-foreground">{metricValue}</p>
		</div>
	</div>
</div>
```

```ts
// ui/src/lib/components/studio/index.ts
export { default as RunSummaryHero } from './RunSummaryHero.svelte';
```

```svelte
<!-- ui/src/routes/runs/[runId]/+page.svelte -->
<StudioPanel title="Analysis summary">
	<RunSummaryHero
		status={run?.status ?? 'loading'}
		viewLabel={currentView.label}
		title={pageModel.summary.title}
		summary={pageModel.summary.summary}
		significance={pageModel.summary.significance}
		nextStep={pageModel.summary.nextStep}
		currentFrame={pageModel.summary.currentFrame}
		metricLabel={focusedMetric?.label ?? 'No primary metric'}
		metricValue={focusedMetric ? formatMetricValue(focusedMetric) : '-'}
	/>
</StudioPanel>
```

- [ ] **Step 4: Re-run the targeted browser test to verify it passes**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx playwright test -g "shows a summary-first completed-run shell before deep analysis panels"
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```bash
cd /Users/saurabh/Projects/Persephone
git add ui/src/lib/components/studio/RunSummaryHero.svelte ui/src/lib/components/studio/index.ts ui/src/routes/runs/[runId]/+page.svelte ui/src/routes/app.e2e.ts
git commit -m "feat: add narrative-first run summary shell"
```

### Task 3: Move explanation, inspector, and artifacts into progressive secondary tabs

**Files:**
- Create: `ui/src/lib/components/studio/RunSecondaryTabs.svelte`
- Modify: `ui/src/routes/runs/[runId]/+page.svelte`
- Modify: `ui/src/lib/studio/inspector.ts`
- Modify: `ui/src/lib/studio/inspector.test.ts`
- Modify: `ui/src/routes/app.e2e.ts`

- [ ] **Step 1: Write the failing tests for progressive disclosure**

```ts
test('hides explanation and debug-heavy sections until the user opens secondary tabs', async ({ page }) => {
	await page.goto('/runs/run-workflow');
	await pausePlaybackIfNeeded(page);

	await expect(page.getByRole('heading', { name: 'Explanation detail' })).toHaveCount(0);
	await page.getByRole('tab', { name: 'Explain' }).click();
	await expect(page.getByText('Delivery risk is clustering on the critical path')).toBeVisible();
});
```

```ts
test('keeps inspector compact until a node is selected', async ({ page }) => {
	await page.goto('/runs/run-workflow');
	await pausePlaybackIfNeeded(page);

	await expect(page.getByText('Select a node, relationship, or field cell')).toHaveCount(0);
	await page.getByRole('tab', { name: 'Inspect' }).click();
	await expect(page.getByText('Select a node, relationship, or field cell')).toBeVisible();
});
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx playwright test -g "hides explanation and debug-heavy sections until the user opens secondary tabs|keeps inspector compact until a node is selected"
```

Expected:

```text
Error: expected "Explanation detail" to have count 0, received 1
Error: expected "Select a node, relationship, or field cell" to have count 0, received 1
```

- [ ] **Step 3: Add the secondary tabs component and compact inspector preview**

```svelte
<!-- ui/src/lib/components/studio/RunSecondaryTabs.svelte -->
<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs';

	let {
		tabs,
		activeTab = $bindable('timeline'),
		children
	}: {
		tabs: Array<{ value: string; label: string }>;
		activeTab?: string;
		children?: import('svelte').Snippet<[string]>;
	} = $props();
</script>

<Tabs.Tabs bind:value={activeTab} class="space-y-4">
	<Tabs.TabsList>
		{#each tabs as tab (tab.value)}
			<Tabs.TabsTrigger value={tab.value}>{tab.label}</Tabs.TabsTrigger>
		{/each}
	</Tabs.TabsList>

	{#each tabs as tab (tab.value)}
		<Tabs.TabsContent value={tab.value}>
			{@render children?.(tab.value)}
		</Tabs.TabsContent>
	{/each}
</Tabs.Tabs>
```

```ts
// ui/src/lib/studio/inspector.ts
export type InspectorPreview = {
	title: string;
	summary: string;
	hasMeaningfulSelection: boolean;
};

export function inspectorPreview(model: InspectorPanelModel): InspectorPreview {
	if (model.kind === 'empty') {
		return {
			title: 'Inspector ready',
			summary: 'Select a node, relationship, or field cell to inspect why it matters.',
			hasMeaningfulSelection: false
		};
	}

	return {
		title: model.title,
		summary: model.summary,
		hasMeaningfulSelection: true
	};
}
```

```svelte
<!-- ui/src/routes/runs/[runId]/+page.svelte -->
<StudioPanel title="Details">
	<RunSecondaryTabs
		tabs={pageModel.secondaryTabs.map((value) => ({ value, label: secondaryTabLabel(value) }))}
		bind:activeTab={activeSecondaryTab}
	>
		{#snippet children(tabValue)}
			{#if tabValue === 'explain'}
				<!-- render explanation cards here -->
			{:else if tabValue === 'inspect'}
				<!-- render full inspector here -->
			{:else if tabValue === 'artifacts'}
				<!-- render artifacts and exports here -->
			{:else if tabValue === 'debug'}
				<!-- render logs + manifest here -->
			{:else}
				<!-- render timeline/recent changes here -->
			{/if}
		{/snippet}
	</RunSecondaryTabs>
</StudioPanel>
```

- [ ] **Step 4: Re-run the targeted tests to verify they pass**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx playwright test -g "hides explanation and debug-heavy sections until the user opens secondary tabs|keeps inspector compact until a node is selected"
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
cd /Users/saurabh/Projects/Persephone
git add ui/src/lib/components/studio/RunSecondaryTabs.svelte ui/src/lib/studio/inspector.ts ui/src/lib/studio/inspector.test.ts ui/src/routes/runs/[runId]/+page.svelte ui/src/routes/app.e2e.ts
git commit -m "feat: move secondary run details behind progressive tabs"
```

### Task 4: Rebuild the route around one primary visualization and one primary metric

**Files:**
- Modify: `ui/src/routes/runs/[runId]/+page.svelte`
- Modify: `ui/src/lib/components/studio/SimulationViewport.svelte`
- Modify: `ui/src/lib/components/studio/MetricDeck.svelte`
- Modify: `ui/src/routes/layout.css`
- Test: `ui/src/routes/app.e2e.ts`

- [ ] **Step 1: Write the failing responsive test for the new first-screen layout**

```ts
test('keeps the summary, primary visualization, and primary metric visible before details on laptop widths', async ({ page }) => {
	await page.setViewportSize({ width: 1280, height: 900 });
	await page.goto('/runs/run-workflow');
	await pausePlaybackIfNeeded(page);

	await expect(page.getByText('Analysis summary')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Viewport' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Delivery risk index analysis' })).toBeVisible();

	const layout = await page.evaluate(() => {
		const lookup = (text: string) =>
			Array.from(document.querySelectorAll('h2')).find((node) => node.textContent?.trim() === text)?.getBoundingClientRect().top ?? null;
		return {
			viewportTop: lookup('Viewport'),
			metricTop: lookup('Delivery risk index analysis'),
			detailsTop: lookup('Details')
		};
	});

	expect(layout.viewportTop).toBeLessThan(layout.detailsTop);
	expect(layout.metricTop).toBeLessThan(layout.detailsTop);
});
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx playwright test -g "keeps the summary, primary visualization, and primary metric visible before details on laptop widths"
```

Expected:

```text
Error: expected metricTop to be less than detailsTop
```

- [ ] **Step 3: Recompose the route into primary analysis surfaces**

```svelte
<!-- ui/src/routes/runs/[runId]/+page.svelte -->
<div class="grid gap-4 2xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)]">
	<div class="grid min-w-0 content-start gap-4">
		<StudioPanel title="Analysis summary">...</StudioPanel>
		<StudioPanel title="Viewport">...</StudioPanel>
	</div>

	<div class="grid min-w-0 content-start gap-4">
		<StudioPanel
			title={focusedMetric ? `${focusedMetric.label} analysis` : 'Metric analysis'}
			description="Focus one metric at a time with playback-aligned charting and threshold context."
		>
			<MetricTimeline ... />
		</StudioPanel>
		{#if inspectorPreviewModel.hasMeaningfulSelection}
			<StudioPanel title="Current selection">
				<p class="text-sm font-medium">{inspectorPreviewModel.title}</p>
				<p class="mt-2 text-sm text-muted-foreground">{inspectorPreviewModel.summary}</p>
			</StudioPanel>
		{/if}
	</div>
</div>

<StudioPanel title="Details">...</StudioPanel>
```

```css
/* ui/src/routes/layout.css */
.run-analysis-primary-grid {
	display: grid;
	gap: 1rem;
}

@media (min-width: 1536px) {
	.run-analysis-primary-grid {
		grid-template-columns: minmax(0, 1.15fr) minmax(22rem, 0.85fr);
		align-items: start;
	}
}
```

- [ ] **Step 4: Re-run the targeted test to verify it passes**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx playwright test -g "keeps the summary, primary visualization, and primary metric visible before details on laptop widths"
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```bash
cd /Users/saurabh/Projects/Persephone
git add ui/src/routes/runs/[runId]/+page.svelte ui/src/lib/components/studio/SimulationViewport.svelte ui/src/lib/components/studio/MetricDeck.svelte ui/src/routes/layout.css ui/src/routes/app.e2e.ts
git commit -m "feat: center run page around primary analysis surfaces"
```

### Task 5: Hide empty fallback content and demote debug/runtime detail

**Files:**
- Modify: `ui/src/routes/runs/[runId]/+page.svelte`
- Modify: `ui/src/lib/studio/run-page.ts`
- Modify: `ui/src/routes/app.e2e.ts`
- Test: `ui/src/lib/studio/run-page.test.ts`

- [ ] **Step 1: Write the failing tests for hiding low-value sections**

```ts
test('suppresses unavailable explanation panels when a plugin emitted no explanation facts', () => {
	const model = buildRunPageModel({
		runStatus: 'completed',
		currentView: { label: 'Heatmap', kind: 'heatmap', surface: 'viewport', purpose: 'Show field values.' },
		narrativeLead: {
			title: 'Stable field state',
			summary: 'The field has diffused into a stable pattern.',
			significance: 'No material domain anomaly is visible.',
			nextStep: 'Use Heatmap to inspect local hotspots.'
		},
		focusedMetric: null,
		explanationCards: [
			{ sourceLabel: 'Unavailable', primaryStatement: 'No interpretation yet', supportingDetail: 'No explanation facts available.' }
		],
		recentChanges: [{ label: 'Scheduler wall time ms', summary: 'Dropped by 0.1 to 0.8.' }],
		inspectorKind: 'empty',
		hasSelection: false,
		pluginSupportsExplanation: false
	});

		expect(model.showExplainTab).toBe(false);
		expect(model.showRecentChanges).toBe(false);
});
```

```ts
test('keeps runtime and manifest detail inside the debug tab only', async ({ page }) => {
	await page.goto('/runs/run-a');
	await pausePlaybackIfNeeded(page);

	await expect(page.getByText('metric stream')).toHaveCount(0);
	await page.getByRole('tab', { name: 'Debug' }).click();
	await expect(page.getByText('metric stream')).toBeVisible();
});
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx vitest run src/lib/studio/run-page.test.ts
bunx playwright test -g "keeps runtime and manifest detail inside the debug tab only"
```

Expected:

```text
Error: expected model.showExplainTab to be false, received true
Error: expected "metric stream" to have count 0, received 1
```

- [ ] **Step 3: Tighten the visibility rules and route rendering**

```ts
// ui/src/lib/studio/run-page.ts
const meaningfulExplain =
	input.pluginSupportsExplanation &&
	input.explanationCards.some((card) => card.sourceLabel !== 'Unavailable' && card.primaryStatement !== 'No interpretation yet');

const meaningfulRecentChanges = input.recentChanges.some(
	(item) => !item.label.toLowerCase().startsWith('scheduler ')
);
```

```svelte
<!-- ui/src/routes/runs/[runId]/+page.svelte -->
{#if tabValue === 'debug'}
	<div class="grid gap-4">
		<StudioPanel title="Runtime streams">...</StudioPanel>
		<StudioPanel title="Run manifest">...</StudioPanel>
	</div>
{/if}
```

- [ ] **Step 4: Re-run the targeted tests to verify they pass**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx vitest run src/lib/studio/run-page.test.ts
bunx playwright test -g "keeps runtime and manifest detail inside the debug tab only"
```

Expected:

```text
✓ src/lib/studio/run-page.test.ts
1 passed
```

- [ ] **Step 5: Commit**

```bash
cd /Users/saurabh/Projects/Persephone
git add ui/src/lib/studio/run-page.ts ui/src/lib/studio/run-page.test.ts ui/src/routes/runs/[runId]/+page.svelte ui/src/routes/app.e2e.ts
git commit -m "feat: hide empty fallbacks and demote debug detail"
```

### Task 6: Verify the full narrative-first slice and refresh visual baselines

**Files:**
- Modify only if verification reveals breakage in files listed above.
- Update: `ui/src/routes/app.e2e.ts-snapshots/run-market-light-chromium-darwin.png`
- Update: `ui/src/routes/app.e2e.ts-snapshots/run-market-dark-chromium-darwin.png`
- Update: `ui/src/routes/app.e2e.ts-snapshots/run-workflow-light-chromium-darwin.png`
- Update: `ui/src/routes/app.e2e.ts-snapshots/run-workflow-dark-chromium-darwin.png`
- Update: `ui/src/routes/app.e2e.ts-snapshots/run-market-metric-cards-tablet-chromium-darwin.png`

- [ ] **Step 1: Run unit tests for the new shared analysis logic**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx vitest run src/lib/studio/run-page.test.ts src/lib/studio/narrative.test.ts src/lib/studio/inspector.test.ts
```

Expected:

```text
All targeted Vitest files pass
```

- [ ] **Step 2: Run responsive browser coverage for the refactored page**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx playwright test -g "summary-first|progressive disclosure|primary analysis surfaces|runtime and manifest detail"
```

Expected:

```text
All targeted Playwright tests pass
```

- [ ] **Step 3: Refresh the run-page visual baselines**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bunx playwright test -g "captures representative run-page visual baselines|keeps metric cards readable" --update-snapshots
```

Expected:

```text
Updated run-page snapshots are written with no remaining failures
```

- [ ] **Step 4: Run the full frontend verification suite**

Run:

```bash
cd /Users/saurabh/Projects/Persephone/ui
bun run check
bun run lint
bun run test:unit
bun run test:e2e
bun run build
```

Expected:

```text
svelte-check found 0 errors and 0 warnings
prettier --check . && eslint . exits 0
vitest passes
playwright passes
vite build succeeds
```

- [ ] **Step 5: Commit**

```bash
cd /Users/saurabh/Projects/Persephone
git add ui/src/routes/app.e2e.ts-snapshots ui/src/routes/app.e2e.ts ui/src/routes/runs/[runId]/+page.svelte ui/src/lib/studio ui/src/lib/components/studio ui/src/routes/layout.css
git commit -m "feat: refactor run page into narrative-first analysis flow"
```

## Follow-Up Note: Plugin enrichment after the shared UI slice

This plan intentionally keeps Python/plugin changes out of the first implementation slice. After the shared page is narrative-first, the next high-value follow-up is to enrich plugins like `us_county_epidemic` and `heat_diffusion` with:

- `PluginManifest.semantics` for stronger labels, headline metrics, and preferred views.
- `Observer.explain(...)` for run/frame/selection facts.

That follow-up will make the simplified UI materially smarter without adding more default chrome.

## Self-Review

- **Spec coverage:** The plan covers the approved product direction: analyst default, completed-run-first, summary-first shell, one primary visualization, one primary metric panel, progressive secondary surfaces, and suppression of empty fallback sections.
- **Placeholder scan:** No `TODO`, `TBD`, or “handle appropriately” steps remain. Every code-changing step includes concrete file paths and code snippets.
- **Type consistency:** The plan consistently uses `buildRunPageModel`, `RunSummaryHero`, `RunSecondaryTabs`, and `inspectorPreview` across later tasks.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-22-run-analysis-narrative-refactor.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
