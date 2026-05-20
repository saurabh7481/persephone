<script lang="ts">
	import type { CompareAlignedRow } from '$lib/api';

	let { rows }: { rows: CompareAlignedRow[] } = $props();

	const maxT = $derived(Math.max(1, ...rows.map((row) => row.t)));
	const maxValue = $derived(
		Math.max(1, ...rows.flatMap((row) => [row.run_a ?? 0, row.run_b ?? 0]))
	);

	function pathFor(key: 'run_a' | 'run_b'): string {
		return rows
			.filter((row) => row[key] !== null)
			.map((row, index) => {
				const x = (row.t / maxT) * 100;
				const y = 100 - ((row[key] ?? 0) / maxValue) * 100;
				return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
			})
			.join(' ');
	}
</script>

<div class="space-y-3">
	<div class="h-64 rounded-md border bg-white p-4">
		{#if rows.length}
			<svg viewBox="0 0 100 100" preserveAspectRatio="none" class="h-full w-full">
				<line x1="0" y1="100" x2="100" y2="100" stroke="#d4d4d8" stroke-width="0.5" />
				<line x1="0" y1="0" x2="0" y2="100" stroke="#d4d4d8" stroke-width="0.5" />
				<path
					d={pathFor('run_a')}
					fill="none"
					stroke="#2563eb"
					stroke-width="2"
					vector-effect="non-scaling-stroke"
				/>
				<path
					d={pathFor('run_b')}
					fill="none"
					stroke="#dc2626"
					stroke-width="2"
					vector-effect="non-scaling-stroke"
				/>
			</svg>
		{:else}
			<div class="grid h-full place-items-center text-sm text-muted-foreground">
				No comparison loaded
			</div>
		{/if}
	</div>
	<div class="flex flex-wrap gap-4 text-sm">
		<span class="flex items-center gap-2"
			><span class="h-2.5 w-2.5 rounded-full bg-blue-600"></span>Run A</span
		>
		<span class="flex items-center gap-2"
			><span class="h-2.5 w-2.5 rounded-full bg-red-600"></span>Run B</span
		>
	</div>
</div>
