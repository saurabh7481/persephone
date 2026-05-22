<script lang="ts">
	import { Maximize2, Pin, PinOff, Rows3 } from '@lucide/svelte';

	import type { MetricDeckItem } from '$lib/studio/metrics';
	import {
		formatDelta,
		formatMetricValue,
		formatPercent,
		formatTimeLabel
	} from '$lib/studio/format';

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

	function formatDeltaLabel(item: MetricDeckItem): string {
		if (!item.previous) return 'No prior point';
		const percent =
			item.deltaPercent === null ? '' : ` (${formatPercent(item.deltaPercent, { signed: true })})`;
		return `${formatDelta(item.delta, { unit: item.unit })}${percent}`;
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

	function formatHeadlineValue(item: MetricDeckItem): string {
		return formatMetricValue(item.current.value, null, {
			compact: Math.abs(item.current.value) >= 100_000
		});
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
			lines.push(`Warning ${formatMetricValue(item.thresholds.warning, item.unit)}`);
		}
		if (typeof item.thresholds.critical === 'number') {
			lines.push(`Critical ${formatMetricValue(item.thresholds.critical, item.unit)}`);
		}
		if (typeof item.thresholds.target === 'number') {
			lines.push(`Target ${formatMetricValue(item.thresholds.target, item.unit)}`);
		}
		return lines;
	}

	function stop(event: MouseEvent) {
		event.stopPropagation();
	}
</script>

<div class="grid gap-3" aria-label="Key metric cards">
	{#if items.length}
		{#each items as item (item.metric)}
			<div
				class={`min-w-0 cursor-pointer rounded-2xl border p-4 transition ${
					focusedMetric === item.metric
						? 'border-primary/60 bg-primary/5 shadow-sm ring-1 ring-primary/20'
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
				<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
					<div class="min-w-0 space-y-3">
						<div class="flex flex-wrap items-start gap-2">
							<div class="min-w-0 flex-1">
								<div class="flex flex-wrap items-center gap-2">
									<p class="min-w-0 text-sm font-semibold break-words">{item.label}</p>
									{#if item.unit}
										<span
											class="rounded-full border border-border/80 px-2 py-0.5 text-[11px] text-muted-foreground"
										>
											{item.unit}
										</span>
									{/if}
								</div>
								<p class="mt-1 text-xs leading-5 text-muted-foreground">
									{item.attentionSummary}
								</p>
							</div>
							<span
								class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${attentionTone(item.attention)}`}
							>
								{item.attentionLabel}
							</span>
						</div>

						<div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
							<div class="min-w-0 space-y-2">
								<p
									class="text-3xl font-semibold tracking-tight break-all"
									title={formatMetricValue(item.current.value, item.unit)}
								>
									{formatHeadlineValue(item)}
								</p>
								<div class="flex flex-wrap gap-2 text-[11px]">
									<span
										class="rounded-full border border-border/80 px-2 py-1 text-muted-foreground"
									>
										{formatDeltaLabel(item)} since previous point
									</span>
									{#if item.headline}
										<span class="rounded-full bg-primary/10 px-2 py-1 font-medium text-primary">
											Headline
										</span>
									{/if}
									{#if item.pinned}
										<span
											class="rounded-full bg-sky-500/10 px-2 py-1 font-medium text-sky-700 dark:text-sky-300"
										>
											Pinned
										</span>
									{/if}
								</div>
							</div>
							<div class="grid gap-1 md:justify-items-end">
								<svg viewBox="0 0 84 28" class="h-10 w-full max-w-28 shrink-0" aria-hidden="true">
									<path
										d={sparklinePath(item.points.map((point) => point.value))}
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										class="text-primary"
									/>
								</svg>
								<p class="text-[11px] text-muted-foreground">{item.attentionLabel}</p>
							</div>
						</div>
					</div>

					<div class="flex shrink-0 items-start gap-1">
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
						class="mt-4 grid gap-2 rounded-xl border border-dashed border-border/80 bg-muted/30 p-3 text-xs text-muted-foreground"
					>
						<div class="grid gap-1 sm:grid-cols-2">
							<p><span class="font-medium text-foreground">Metric id:</span> {item.metric}</p>
							<p>
								<span class="font-medium text-foreground">Selected time:</span>
								{formatTimeLabel(item.current.t)}
							</p>
						</div>
						<p>{item.attentionSummary}</p>
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
