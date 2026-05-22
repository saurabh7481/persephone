<script lang="ts">
	import { line } from 'd3';

	import type { EventRecord, MetricRecord, SimulationFrame } from '$lib/api-client';
	import {
		formatMetricValue,
		formatNumber,
		formatTimeLabel,
		humanizeIdentifier
	} from '$lib/studio/format';
	import {
		currentMetricCards,
		eventMarkers,
		frameTickMarkers,
		metricTimelineSeries,
		timelineDomain,
		timeFromBrush,
		timeFromPointer,
		xScale,
		yScale
	} from '$lib/studio/timeline';

	let {
		records,
		events = [],
		frames = [],
		selectedTime = 0,
		showCards = true,
		thresholds,
		onSelectTime
	}: {
		records: MetricRecord[];
		events?: EventRecord[];
		frames?: SimulationFrame[];
		selectedTime?: number;
		showCards?: boolean;
		thresholds?: { warning?: number; critical?: number; target?: number };
		onSelectTime?: (time: number) => void;
	} = $props();

	const palette = ['#2f7dd3', '#d44f42', '#2f9d68', '#7b61c9', '#c78a1c', '#18879a'];
	const width = 720;
	const height = 220;
	const margin = { top: 18, right: 20, bottom: 34, left: 46 };
	const plotWidth = width - margin.left - margin.right;
	const plotHeight = height - margin.top - margin.bottom;

	let brushStart = $state('');
	let brushEnd = $state('');
	let dragging = $state(false);

	const series = $derived(metricTimelineSeries(records).slice(0, 6));
	const domain = $derived(timelineDomain(records, events, frames));
	const markerEvents = $derived(eventMarkers(events));
	const markerFrames = $derived(frameTickMarkers(frames));
	const cards = $derived(currentMetricCards(records, selectedTime || domain.tMin));
	const x = $derived(xScale(plotWidth, domain));
	const y = $derived(yScale(plotHeight, domain));
	const selectedX = $derived(margin.left + x(selectedTime || domain.tMin));
	const brushedRange = $derived(
		brushStart !== '' && brushEnd !== ''
			? timeFromBrush([Number(brushStart), Number(brushEnd)], plotWidth, domain)
			: null
	);
	const chartLine = $derived(
		line<MetricRecord>()
			.x((point) => margin.left + x(point.t))
			.y((point) => margin.top + y(point.value))
	);

	function selectFromEvent(event: PointerEvent | MouseEvent) {
		const target = event.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		const xPosition = ((event.clientX - rect.left) / rect.width) * width - margin.left;
		onSelectTime?.(timeFromPointer(xPosition, plotWidth, domain));
	}

	function selectFromKeyboard(event: KeyboardEvent) {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		onSelectTime?.((domain.tMin + domain.tMax) / 2);
	}

	function startBrush(event: PointerEvent) {
		dragging = true;
		const point = brushPoint(event);
		brushStart = String(point);
		brushEnd = String(point);
	}

	function updateBrush(event: PointerEvent) {
		if (!dragging) return;
		brushEnd = String(brushPoint(event));
	}

	function finishBrush(event: PointerEvent) {
		if (!dragging) return;
		dragging = false;
		brushEnd = String(brushPoint(event));
		if (brushedRange) onSelectTime?.(brushedRange.start);
	}

	function brushPoint(event: PointerEvent): number {
		const target = event.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		return Math.min(
			plotWidth,
			Math.max(0, ((event.clientX - rect.left) / rect.width) * width - margin.left)
		);
	}

	function pathFor(points: MetricRecord[]): string {
		return chartLine(points) ?? '';
	}

	function markerX(time: number): number {
		return margin.left + x(time);
	}

	function axisTicks(): number[] {
		return x.ticks(5);
	}
</script>

<div class="metric-timeline">
	{#if showCards}
		<div class="metric-timeline-cards" aria-label="Current metric cards">
			{#each cards as card (card.metric)}
				<div class="metric-timeline-card">
					<p class="studio-eyebrow">{humanizeIdentifier(card.metric)}</p>
					<p>{formatMetricValue(card.value)}</p>
					<span>{formatTimeLabel(card.t)}</span>
				</div>
			{/each}
		</div>
	{/if}

	<div class="metric-timeline-chart">
		{#if records.length}
			<button
				type="button"
				class="metric-timeline-hit-target"
				aria-label="Metric timeline"
				onclick={selectFromEvent}
				onkeydown={selectFromKeyboard}
				onpointerdown={startBrush}
				onpointermove={updateBrush}
				onpointerup={finishBrush}
				onpointerleave={finishBrush}
			>
				<svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
					<rect
						x={margin.left}
						y={margin.top}
						width={plotWidth}
						height={plotHeight}
						class="metric-timeline-plot"
					/>

					{#each axisTicks() as tick (tick)}
						<line
							x1={markerX(tick)}
							x2={markerX(tick)}
							y1={margin.top}
							y2={margin.top + plotHeight}
							class="metric-timeline-grid"
						/>
						<text
							x={markerX(tick)}
							y={height - 10}
							text-anchor="middle"
							class="metric-timeline-axis"
						>
							{formatNumber(tick, { maximumFractionDigits: 1 })}
						</text>
					{/each}

					{#each markerFrames as marker (marker.frameId)}
						<line
							x1={markerX(marker.t)}
							x2={markerX(marker.t)}
							y1={margin.top}
							y2={margin.top + plotHeight}
							class="metric-timeline-frame-marker"
						/>
					{/each}

					{#each markerEvents as marker, index (`${marker.t}:${marker.label}:${index}`)}
						<line
							x1={markerX(marker.t)}
							x2={markerX(marker.t)}
							y1={margin.top}
							y2={margin.top + plotHeight}
							class="metric-timeline-event-marker"
						/>
						<circle
							cx={markerX(marker.t)}
							cy={margin.top + 12 + index * 8}
							r="3"
							class="metric-timeline-event-dot"
						>
							<title>{marker.label}</title>
						</circle>
					{/each}

					{#if brushedRange}
						<rect
							x={margin.left + Math.min(Number(brushStart), Number(brushEnd))}
							y={margin.top}
							width={Math.abs(Number(brushEnd) - Number(brushStart))}
							height={plotHeight}
							class="metric-timeline-brush"
						/>
					{/if}

					{#each series as item, index (item.metric)}
						<path
							d={pathFor(item.points)}
							fill="none"
							stroke={palette[index % palette.length]}
							stroke-width="2.5"
							vector-effect="non-scaling-stroke"
						/>
					{/each}

					{#if typeof thresholds?.target === 'number'}
						<line
							x1={margin.left}
							x2={margin.left + plotWidth}
							y1={margin.top + y(thresholds.target)}
							y2={margin.top + y(thresholds.target)}
							stroke="#2f9d68"
							stroke-width="1.5"
							stroke-dasharray="4 4"
						/>
					{/if}
					{#if typeof thresholds?.warning === 'number'}
						<line
							x1={margin.left}
							x2={margin.left + plotWidth}
							y1={margin.top + y(thresholds.warning)}
							y2={margin.top + y(thresholds.warning)}
							stroke="#c78a1c"
							stroke-width="1.5"
							stroke-dasharray="6 5"
						/>
					{/if}
					{#if typeof thresholds?.critical === 'number'}
						<line
							x1={margin.left}
							x2={margin.left + plotWidth}
							y1={margin.top + y(thresholds.critical)}
							y2={margin.top + y(thresholds.critical)}
							stroke="#d44f42"
							stroke-width="1.5"
							stroke-dasharray="8 5"
						/>
					{/if}

					<line
						x1={selectedX}
						x2={selectedX}
						y1={margin.top}
						y2={margin.top + plotHeight}
						class="metric-timeline-selected"
					/>
				</svg>
			</button>
		{:else}
			<div class="grid h-full place-items-center text-sm text-muted-foreground">No metrics yet</div>
		{/if}
	</div>

	<div class="metric-timeline-footer">
		<div class="metric-timeline-legend">
			{#each series as item, index (item.metric)}
				<span>
					<i style={`background-color: ${palette[index % palette.length]}`}></i>
					{item.metric}
				</span>
			{/each}
		</div>
		<div class="metric-timeline-status">
			<span>Selected time {formatTimeLabel(selectedTime, { prefix: '' })}</span>
			<span>Events {markerEvents.length}</span>
			<span>Frames {markerFrames.length}</span>
			{#if brushedRange}
				<span>
					Brush {formatNumber(brushedRange.start)}-{formatNumber(brushedRange.end)}
				</span>
			{/if}
		</div>
	</div>
</div>
