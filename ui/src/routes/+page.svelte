<script lang="ts">
	import { resolve } from '$app/paths';
	import { Boxes, ChartNoAxesCombined, ListStart, Play } from '@lucide/svelte';

	import { StudioPanel, StudioWorkbench } from '$lib/components/studio';
</script>

<StudioWorkbench
	title="Simulation Studio"
	subtitle="Create experiments, open replay runs, inspect frames, and compare outcomes."
>
	{#snippet left()}
		<div class="grid gap-3 p-3">
			<StudioPanel title="Start">
				<div class="grid gap-2">
					<a class="studio-action-link" href={resolve('/experiments')}>
						<Play size={16} />
						<span>Create experiment</span>
					</a>
					<a class="studio-action-link" href={resolve('/runs')}>
						<ListStart size={16} />
						<span>Open run catalog</span>
					</a>
					<a class="studio-action-link" href={resolve('/compare')}>
						<ChartNoAxesCombined size={16} />
						<span>Compare results</span>
					</a>
					<a class="studio-action-link" href={resolve('/plugins')}>
						<Boxes size={16} />
						<span>Review plugins</span>
					</a>
				</div>
			</StudioPanel>
		</div>
	{/snippet}

	{#snippet viewport()}
		<div class="studio-viewport-empty">
			<div>
				<p class="studio-eyebrow">Studio · ready</p>
				<h2>No run selected</h2>
				<p>Select an existing run or create a new experiment to start live playback.</p>
			</div>
		</div>
	{/snippet}

	{#snippet inspector()}
		<div class="grid gap-3 p-3">
			<StudioPanel title="Inspector">
				<div class="grid gap-2 text-sm">
					<div>
						<p class="text-xs text-muted-foreground">Selected frame</p>
						<p class="font-mono text-xs">none</p>
					</div>
					<div>
						<p class="text-xs text-muted-foreground">Selected object</p>
						<p class="font-mono text-xs">none</p>
					</div>
					<div>
						<p class="text-xs text-muted-foreground">Mode</p>
						<p>Choose a run to enter replay or live playback.</p>
					</div>
				</div>
			</StudioPanel>
		</div>
	{/snippet}

	{#snippet dock()}
		<div class="grid gap-3 p-3 md:grid-cols-3">
			<StudioPanel title="Live playback">
				<p class="text-sm text-muted-foreground">
					Field and graph frames render in the central viewport once a run is active.
				</p>
			</StudioPanel>
			<StudioPanel title="Analysis dock">
				<p class="text-sm text-muted-foreground">
					Metrics, events, frames, artifacts, and logs stay synchronized with playback.
				</p>
			</StudioPanel>
			<StudioPanel title="Technical detail">
				<p class="text-sm text-muted-foreground">
					Runtime metadata and plugin-driven schemas remain available on demand.
				</p>
			</StudioPanel>
		</div>
	{/snippet}
</StudioWorkbench>
