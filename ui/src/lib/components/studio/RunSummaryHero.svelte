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
			<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
				Why it matters
			</p>
			<p class="mt-2 text-sm leading-6">{significance}</p>
		</div>
		<div class="rounded-xl border bg-background/70 p-3">
			<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
				What to inspect next
			</p>
			<p class="mt-2 text-sm leading-6">{nextStep}</p>
		</div>
		<div class="rounded-xl border bg-muted/25 p-3">
			<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
				Primary metric
			</p>
			<p class="mt-2 text-sm font-semibold">{metricLabel}</p>
			<p class="mt-1 text-xs text-muted-foreground">{metricValue}</p>
		</div>
	</div>
</div>
