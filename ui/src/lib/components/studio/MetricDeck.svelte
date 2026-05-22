<script lang="ts">
	import { Maximize2, Pin, PinOff, Rows3 } from '@lucide/svelte';

	import type { MetricDeckItem } from '$lib/studio/metrics';

	let {
		items,
		focusedMetric = null,
		expandedMetrics = [],
		onFocusMetric,
		onToggleExpanded,
		onTogglePin,
		onOpenFullscreen
	}: {
		items: MetricDeckItem[];
		focusedMetric?: string | null;
		expandedMetrics?: string[];
		onFocusMetric?: (metric: string) => void;
		onToggleExpanded?: (metric: string) => void;
		onTogglePin?: (metric: string) => void;
		onOpenFullscreen?: (metric: string) => void;
	} = $props();

	function formatValue(value: number, unit: string | null): string {
		const compact = Math.abs(value) >= 1000 ? value.toLocaleString() : value.toFixed(2);
		return unit ? `${compact} ${unit}` : compact;
	}

	function formatDelta(item: MetricDeckItem): string {
		if (!item.previous) return 'No prior point';
		const sign = item.delta > 0 ? '+' : '';
		const percent =
			item.deltaPercent === null ? '' : ` (${sign}${(item.deltaPercent * 100).toFixed(1)}%)`;
		return `${sign}${item.delta.toFixed(2)}${percent}`;
	}

	function attentionLabel(attention: MetricDeckItem['attention']): string {
		switch (attention) {
			case 'critical':
				return 'Critical';
			case 'rising_concern':
				return 'Rising concern';
			case 'improving':
				return 'Improving';
			default:
				return 'Stable';
		}
	}

	function attentionTone(attention: MetricDeckItem['attention']): string {
		switch (attention) {
			case 'critical':
				return 'border-red-300 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200';
			case 'rising_concern':
				return 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200';
			case 'improving':
				return 'border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200';
			default:
				return 'border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-200';
		}
	}

	function sparklinePath(values: number[]): string {
		if (!values.length) return '';
		const width = 84;
		const height = 28;
		const min = Math.min(...values);
		const max = Math.max(...values);
		const range = max - min || 1;
		return values
			.map((value, index) => {
				const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
				const y = height - ((value - min) / range) * height;
				return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
			})
			.join(' ');
	}

	function thresholdSummary(item: MetricDeckItem): string[] {
		const lines: string[] = [];
		if (typeof item.thresholds.warning === 'number') {
			lines.push(`Warning ${formatValue(item.thresholds.warning, item.unit)}`);
		}
		if (typeof item.thresholds.critical === 'number') {
			lines.push(`Critical ${formatValue(item.thresholds.critical, item.unit)}`);
		}
		if (typeof item.thresholds.target === 'number') {
			lines.push(`Target ${formatValue(item.thresholds.target, item.unit)}`);
		}
		return lines;
	}

	function stop(event: MouseEvent) {
		event.stopPropagation();
	}
</script>

<div class="grid gap-3">
	{#if items.length}
		{#each items as item (item.metric)}
			<div
				class={`cursor-pointer rounded-xl border p-3 transition ${
					focusedMetric === item.metric
						? 'border-primary/60 bg-primary/5 shadow-sm'
						: 'border-border bg-background/80 hover:border-primary/30'
				}`}
				role="button"
				tabindex="0"
				onclick={() => onFocusMetric?.(item.metric)}
				onkeydown={(event) => {
					if (event.key === 'Enter' || event.key === ' ') {
						event.preventDefault();
						onFocusMetric?.(item.metric);
					}
				}}
			>
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0 space-y-2">
						<div class="flex flex-wrap items-center gap-2">
							<p class="truncate text-sm font-semibold">{item.label}</p>
							<span
								class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${attentionTone(item.attention)}`}
							>
								{attentionLabel(item.attention)}
							</span>
							{#if item.headline}
								<span
									class="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary"
								>
									Headline
								</span>
							{/if}
							{#if item.pinned}
								<span
									class="rounded-full bg-sky-500/10 px-2 py-0.5 text-[11px] font-medium text-sky-700 dark:text-sky-300"
								>
									Pinned
								</span>
							{/if}
						</div>
						<div class="flex items-end justify-between gap-3">
							<div>
								<p class="text-2xl font-semibold tracking-tight">
									{formatValue(item.current.value, item.unit)}
								</p>
								<p class="text-xs text-muted-foreground">
									{formatDelta(item)} since previous point
								</p>
							</div>
							<svg viewBox="0 0 84 28" class="h-8 w-24 shrink-0" aria-hidden="true">
								<path
									d={sparklinePath(item.points.map((point) => point.value))}
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									class="text-primary"
								/>
							</svg>
						</div>
					</div>

					<div class="flex shrink-0 items-center gap-1">
						<button
							type="button"
							class="rounded-md border border-border p-1.5 text-muted-foreground hover:text-foreground"
							aria-label={item.pinned ? `Unpin ${item.label}` : `Pin ${item.label}`}
							aria-pressed={item.pinned}
							onclick={(event) => {
								stop(event);
								onTogglePin?.(item.metric);
							}}
						>
							{#if item.pinned}
								<PinOff size={14} />
							{:else}
								<Pin size={14} />
							{/if}
						</button>
						<button
							type="button"
							class="rounded-md border border-border p-1.5 text-muted-foreground hover:text-foreground"
							aria-label={`Expand ${item.label}`}
							aria-pressed={expandedMetrics.includes(item.metric)}
							onclick={(event) => {
								stop(event);
								onToggleExpanded?.(item.metric);
							}}
						>
							<Rows3 size={14} />
						</button>
						<button
							type="button"
							class="rounded-md border border-border p-1.5 text-muted-foreground hover:text-foreground"
							aria-label={`Open ${item.label} in full-screen chart`}
							onclick={(event) => {
								stop(event);
								onOpenFullscreen?.(item.metric);
							}}
						>
							<Maximize2 size={14} />
						</button>
					</div>
				</div>

				{#if expandedMetrics.includes(item.metric)}
					<div
						class="mt-3 grid gap-2 rounded-lg border border-dashed border-border/80 bg-muted/30 p-3 text-xs text-muted-foreground"
					>
						<div class="grid gap-1 sm:grid-cols-2">
							<p><span class="font-medium text-foreground">Metric id:</span> {item.metric}</p>
							<p>
								<span class="font-medium text-foreground">Selected time:</span>
								t={item.current.t.toFixed(2)}
							</p>
						</div>
						{#if thresholdSummary(item).length}
							<div class="flex flex-wrap gap-2">
								{#each thresholdSummary(item) as line (line)}
									<span class="rounded-full border border-border px-2 py-0.5">{line}</span>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{/each}
	{:else}
		<div class="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
			Metrics will appear here as the run emits observations.
		</div>
	{/if}
</div>
