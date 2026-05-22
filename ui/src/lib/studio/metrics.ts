import type { MetricDefinition, MetricRecord, PluginSemantics } from '$lib/api-client';
import { formatMetricValue, formatPercent, humanizeIdentifier } from '$lib/studio/format';

export type MetricAttention = 'stable' | 'rising_concern' | 'critical' | 'improving';

export type MetricThresholds = {
	warning?: number;
	critical?: number;
	target?: number;
};

export type MetricDeckItem = {
	metric: string;
	label: string;
	unit: string | null;
	current: MetricRecord;
	previous: MetricRecord | null;
	delta: number;
	deltaPercent: number | null;
	attention: MetricAttention;
	attentionLabel: string;
	attentionSummary: string;
	headline: boolean;
	pinned: boolean;
	thresholds: MetricThresholds;
	points: MetricRecord[];
};

export function buildMetricDeck({
	records,
	pluginSemantics,
	selectedTime,
	pinnedMetrics = new Set<string>()
}: {
	records: MetricRecord[];
	pluginSemantics: PluginSemantics[];
	selectedTime: number;
	pinnedMetrics?: Set<string>;
}): MetricDeckItem[] {
	const definitions = metricDefinitions(pluginSemantics);
	const headlines = headlineMetricNames(pluginSemantics);

	return Array.from(groupMetricSeries(records))
		.filter(([metric]) => !metric.startsWith('scheduler.'))
		.map(([metric, points]) => {
			const current = nearestMetricPoint(points, selectedTime) ?? points.at(-1);
			if (!current) return null;
			const currentIndex = points.findIndex((point) => point === current);
			const previous = currentIndex > 0 ? points[currentIndex - 1] : null;
			const delta = previous ? current.value - previous.value : 0;
			const deltaPercent =
				previous && previous.value !== 0 ? delta / Math.abs(previous.value) : previous ? 0 : null;
			const definition = definitions.get(metric);
			const thresholds = readThresholds(current, definition);
			return {
				metric,
				label: definition?.label ?? humanizeIdentifier(metric),
				unit: definition?.unit ?? null,
				current,
				previous,
				delta,
				deltaPercent,
				attention: metricAttention(current, previous, thresholds),
				attentionLabel: attentionLabel(metricAttention(current, previous, thresholds)),
				attentionSummary: attentionSummary({
					attention: metricAttention(current, previous, thresholds),
					current,
					previous,
					thresholds,
					unit: definition?.unit ?? null,
					deltaPercent
				}),
				headline: headlines.has(metric),
				pinned: pinnedMetrics.has(metric),
				thresholds,
				points
			} satisfies MetricDeckItem;
		})
		.filter((item): item is MetricDeckItem => item !== null)
		.sort(compareDeckItems);
}

export function togglePinnedMetric(current: Set<string>, metric: string): Set<string> {
	const next = new Set(current);
	if (next.has(metric)) next.delete(metric);
	else next.add(metric);
	return next;
}

export function metricDefinitions(
	pluginSemantics: PluginSemantics[]
): Map<string, MetricDefinition> {
	const definitions = new Map<string, MetricDefinition>();
	for (const plugin of pluginSemantics) {
		for (const [metric, definition] of Object.entries(plugin.semantics.metric_schema ?? {})) {
			definitions.set(metric, definition);
		}
	}
	return definitions;
}

export function headlineMetricNames(pluginSemantics: PluginSemantics[]): Set<string> {
	const headlines = new Set<string>();
	for (const plugin of pluginSemantics) {
		for (const [metric, definition] of Object.entries(plugin.semantics.metric_schema ?? {})) {
			if (definition.headline) headlines.add(metric);
		}
	}
	return headlines;
}

function compareDeckItems(left: MetricDeckItem, right: MetricDeckItem): number {
	return (
		Number(right.pinned) - Number(left.pinned) ||
		Number(right.headline) - Number(left.headline) ||
		attentionPriority(right.attention) - attentionPriority(left.attention) ||
		Math.abs(right.deltaPercent ?? 0) - Math.abs(left.deltaPercent ?? 0) ||
		Math.abs(right.current.value) - Math.abs(left.current.value) ||
		left.metric.localeCompare(right.metric)
	);
}

function attentionPriority(attention: MetricAttention): number {
	switch (attention) {
		case 'critical':
			return 3;
		case 'rising_concern':
			return 2;
		case 'improving':
			return 1;
		default:
			return 0;
	}
}

function metricAttention(
	current: MetricRecord,
	previous: MetricRecord | null,
	thresholds: MetricThresholds
): MetricAttention {
	if (typeof thresholds.critical === 'number' && current.value >= thresholds.critical) {
		return 'critical';
	}

	if (previous && typeof thresholds.warning === 'number') {
		const wasElevated = previous.value >= thresholds.warning;
		const isElevated = current.value >= thresholds.warning;
		if (wasElevated && current.value < previous.value) return 'improving';
		if (isElevated && current.value >= previous.value) return 'rising_concern';
	}

	if (!previous) return 'stable';
	const baseline = Math.max(Math.abs(previous.value), 1);
	const deltaRatio = (current.value - previous.value) / baseline;
	if (deltaRatio >= 0.15) return 'rising_concern';
	if (deltaRatio <= -0.12) return 'improving';
	return 'stable';
}

function attentionLabel(attention: MetricAttention): string {
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

function attentionSummary({
	attention,
	current,
	previous,
	thresholds,
	unit,
	deltaPercent
}: {
	attention: MetricAttention;
	current: MetricRecord;
	previous: MetricRecord | null;
	thresholds: MetricThresholds;
	unit: string | null;
	deltaPercent: number | null;
}): string {
	switch (attention) {
		case 'critical':
			if (typeof thresholds.critical === 'number') {
				return `Current value is above the critical threshold of ${formatMetricValue(thresholds.critical, unit)}.`;
			}
			return 'Current value is in the critical range and should be inspected first.';
		case 'rising_concern':
			if (typeof thresholds.warning === 'number' && current.value >= thresholds.warning) {
				return 'Current value is above warning and still climbing.';
			}
			return deltaPercent == null
				? 'Current value is climbing faster than the recent baseline.'
				: `Current value is up ${formatPercent(deltaPercent, { signed: true })} from the previous point.`;
		case 'improving':
			return 'Current value is moving back toward the safer range.';
		default:
			if (!previous) return 'This metric has only one sampled point so far.';
			return 'Current value is holding steady relative to the recent baseline.';
	}
}

function groupMetricSeries(records: MetricRecord[]): Map<string, MetricRecord[]> {
	const grouped = new Map<string, MetricRecord[]>();
	for (const record of records) {
		const existing = grouped.get(record.metric) ?? [];
		existing.push(record);
		grouped.set(record.metric, existing);
	}
	for (const points of grouped.values()) {
		points.sort((left, right) => left.t - right.t);
	}
	return grouped;
}

function nearestMetricPoint(points: MetricRecord[], selectedTime: number): MetricRecord | null {
	return points.reduce<MetricRecord | null>((nearest, point) => {
		if (!nearest) return point;
		return Math.abs(point.t - selectedTime) < Math.abs(nearest.t - selectedTime) ? point : nearest;
	}, null);
}

function readThresholds(
	current: MetricRecord,
	definition: MetricDefinition | undefined
): MetricThresholds {
	const definitionExtras = (definition ?? {}) as Record<string, unknown>;
	const recordExtras = current as Record<string, unknown>;
	const nested =
		(recordExtras.thresholds as Record<string, unknown> | undefined) ??
		(definitionExtras.thresholds as Record<string, unknown> | undefined) ??
		{};

	return {
		warning: numberValue(recordExtras.warning_threshold ?? nested.warning),
		critical: numberValue(recordExtras.critical_threshold ?? nested.critical),
		target: numberValue(recordExtras.target ?? definitionExtras.target ?? nested.target)
	};
}

function numberValue(value: unknown): number | undefined {
	return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}
