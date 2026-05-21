<script lang="ts">
	let leftOpen = $state(true);
	let inspectorOpen = $state(true);
	let dockOpen = $state(true);

	let {
		title,
		subtitle,
		left,
		viewport,
		inspector,
		dock
	}: {
		title: string;
		subtitle?: string;
		left?: import('svelte').Snippet;
		viewport?: import('svelte').Snippet;
		inspector?: import('svelte').Snippet;
		dock?: import('svelte').Snippet;
	} = $props();
</script>

<div class="studio-workbench">
	<header class="studio-workbench-header">
		<div>
			<h1>{title}</h1>
			{#if subtitle}
				<p>{subtitle}</p>
			{/if}
		</div>
		<div class="studio-workbench-actions" aria-label="Panel visibility">
			<button type="button" aria-pressed={leftOpen} onclick={() => (leftOpen = !leftOpen)}>
				Controls
			</button>
			<button
				type="button"
				aria-pressed={inspectorOpen}
				onclick={() => (inspectorOpen = !inspectorOpen)}
			>
				Inspector
			</button>
			<button type="button" aria-pressed={dockOpen} onclick={() => (dockOpen = !dockOpen)}>
				Dock
			</button>
		</div>
	</header>

	<div
		class="studio-workbench-grid"
		data-left-open={leftOpen}
		data-inspector-open={inspectorOpen}
		data-dock-open={dockOpen}
	>
		{#if leftOpen}
			<aside class="studio-workbench-left" aria-label="Experiment controls">
				{@render left?.()}
			</aside>
		{/if}
		<section class="studio-workbench-viewport" aria-label="Simulation playback viewport">
			{@render viewport?.()}
		</section>
		{#if inspectorOpen}
			<aside class="studio-workbench-inspector" aria-label="Inspector">
				{@render inspector?.()}
			</aside>
		{/if}
		{#if dockOpen}
			<section class="studio-workbench-dock" aria-label="Analysis dock">
				{@render dock?.()}
			</section>
		{/if}
	</div>
</div>
