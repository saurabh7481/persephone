<script lang="ts">
	import type { MetricRecord } from '$lib/api';
	import { metricSeries } from '$lib/api';

	let { records }: { records: MetricRecord[] } = $props();

	const palette = ['#2563eb', '#dc2626', '#059669', '#7c3aed', '#ea580c', '#0891b2'];

	const series = $derived(metricSeries(records));
	const selected = $derived(
		Object.keys(series)
			.filter((metric) => !metric.startsWith('scheduler.'))
			.slice(0, 6)
	);
	const maxT = $derived(Math.max(1, ...records.map((record) => record.t)));
	const maxValue = $derived(Math.max(1, ...records.map((record) => record.value)));

	function pathFor(points: MetricRecord[]): string {
		return points
			.map((point, index) => {
				const x = (point.t / maxT) * 100;
				const y = 100 - (point.value / maxValue) * 100;
				return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
			})
			.join(' ');
	}
</script>

<div class="space-y-4">
	<div class="h-64 rounded-md border bg-white p-4">
		{#if records.length}
			<svg viewBox="0 0 100 100" preserveAspectRatio="none" class="h-full w-full">
				<line x1="0" y1="100" x2="100" y2="100" stroke="#d4d4d8" stroke-width="0.5" />
				<line x1="0" y1="0" x2="0" y2="100" stroke="#d4d4d8" stroke-width="0.5" />
				{#each selected as metric (metric)}
					<path
						d={pathFor(series[metric] ?? [])}
						fill="none"
						stroke={palette[selected.indexOf(metric) % palette.length]}
						stroke-width="2"
						vector-effect="non-scaling-stroke"
					/>
				{/each}
			</svg>
		{:else}
			<div class="grid h-full place-items-center text-sm text-muted-foreground">No metrics yet</div>
		{/if}
	</div>

	<div class="flex flex-wrap gap-3 text-sm">
		{#each selected as metric (metric)}
			<div class="flex items-center gap-2">
				<span
					class="h-2.5 w-2.5 rounded-full"
					style={`background-color: ${palette[selected.indexOf(metric) % palette.length]}`}
				></span>
				<span>{metric}</span>
			</div>
		{/each}
	</div>
</div>
