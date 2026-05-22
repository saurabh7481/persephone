import { group } from 'd3';

import type {
	EventRecord,
	ExplanationResponse,
	MetricRecord,
	SimulationFrame
} from '$lib/api-client';

export type NarrativeCard = {
	label: string;
	summary: string;
	severity: 'info' | 'notice' | 'warning' | 'critical';
};

export type NarrativeMilestone = {
	id: string;
	kind: 'peak' | 'threshold_crossing' | 'anomaly_end' | 'event_burst' | 'fact';
	title: string;
	summary: string;
	t: number;
	severity: 'info' | 'notice' | 'warning' | 'critical';
	metric?: string;
};

export function extractMilestones({
	metrics,
	events,
	frames,
	explanation
}: {
	metrics: MetricRecord[];
	events: EventRecord[];
	frames: SimulationFrame[];
	explanation: ExplanationResponse | null;
}): NarrativeMilestone[] {
	const milestones: NarrativeMilestone[] = [];
	const series = metricSeries(metrics);
	const dominantPeak = dominantPeakPoint(series);

	for (const [metric, points] of series) {
		const peak = highestPoint(points);
		if (peak && dominantPeak && dominantPeak.metric === metric && dominantPeak.point.t === peak.t) {
			milestones.push({
				id: `peak:${metric}:${peak.t}`,
				kind: 'peak',
				title: `${metric} peak`,
				summary: `${metric} reached ${peak.value}`,
				t: peak.t,
				severity: thresholdSeverity(peak),
				metric
			});
		}

		const crossing = criticalThresholdCrossing(points);
		if (crossing) {
			milestones.push({
				id: `threshold:${metric}:${crossing.t}`,
				kind: 'threshold_crossing',
				title: `${metric} crossed the critical threshold`,
				summary: `${metric} moved above the configured critical threshold.`,
				t: crossing.t,
				severity: 'critical',
				metric
			});
		}

		const anomalyEnd = anomalyEndPoint(points);
		if (anomalyEnd) {
			milestones.push({
				id: `anomaly-end:${metric}:${anomalyEnd.t}`,
				kind: 'anomaly_end',
				title: `${metric} snapped back toward baseline`,
				summary: `${metric} dropped sharply after its recent spike.`,
				t: anomalyEnd.t,
				severity: 'warning',
				metric
			});
		}
	}

	const burst = majorEventBurst(events);
	if (burst) {
		milestones.push({
			id: `burst:${burst.t}`,
			kind: 'event_burst',
			title: 'Major event burst',
			summary: `${burst.count} events landed in a short interval.`,
			t: burst.t,
			severity: 'notice'
		});
	}

	for (const fact of explanation?.interpretation?.facts ?? []) {
		milestones.push({
			id: `fact:${fact.kind}:${fact.t}:${fact.title}`,
			kind: 'fact',
			title: fact.title,
			summary: fact.summary,
			t: fact.t,
			severity: fact.severity
		});
	}

	const frameMin = Math.min(...frames.map((frame) => frame.t), Infinity);
	return milestones
		.filter((milestone) => Number.isFinite(milestone.t) && milestone.t >= frameMin)
		.sort(
			(left, right) =>
				left.t - right.t || milestonePriority(left.kind) - milestonePriority(right.kind)
		);
}

export function recentChangeCards({
	metrics,
	events,
	selectedTime,
	explanation
}: {
	metrics: MetricRecord[];
	events: EventRecord[];
	selectedTime: number;
	explanation: ExplanationResponse | null;
}): NarrativeCard[] {
	const cards: NarrativeCard[] = [];
	const topMetric = topMetricDelta(metrics, selectedTime);
	if (topMetric) {
		cards.push({
			label: topMetric.metric,
			summary: `${topMetric.delta >= 0 ? 'Up' : 'Down'} ${Math.abs(topMetric.delta).toFixed(1)} from the previous sample`,
			severity: topMetric.severity
		});
	}

	const recentEvents = events.filter(
		(event) => typeof event.t === 'number' && event.t >= selectedTime - 1 && event.t <= selectedTime
	);
	if (recentEvents.length >= 2) {
		cards.push({
			label: 'Event burst',
			summary: `${recentEvents.length} events landed within the recent activity window`,
			severity: recentEvents.length >= 3 ? 'notice' : 'info'
		});
	}

	const summary = explanation?.interpretation?.summary;
	if (summary) {
		cards.push({
			label: 'Interpretation',
			summary: summary.summary,
			severity: summary.severity
		});
	}

	return cards;
}

export function milestonePlaybackTarget(
	milestone: NarrativeMilestone,
	frames: SimulationFrame[]
): { time: number; frameId: string | null } {
	const frame = frames.reduce<SimulationFrame | null>((nearest, candidate) => {
		if (!nearest) return candidate;
		return Math.abs(candidate.t - milestone.t) < Math.abs(nearest.t - milestone.t)
			? candidate
			: nearest;
	}, null);
	return {
		time: frame?.t ?? milestone.t,
		frameId: frame?.frame_id ?? null
	};
}

function metricSeries(records: MetricRecord[]): Map<string, MetricRecord[]> {
	return new Map(
		group(records, (record) => record.metric)
			.entries()
			.map(([metric, points]) => [metric, [...points].sort((left, right) => left.t - right.t)])
	);
}

function highestPoint(points: MetricRecord[]): MetricRecord | null {
	return points.reduce<MetricRecord | null>((highest, point) => {
		if (!highest || point.value > highest.value) return point;
		return highest;
	}, null);
}

function dominantPeakPoint(
	series: Map<string, MetricRecord[]>
): { metric: string; point: MetricRecord } | null {
	let best: { metric: string; point: MetricRecord } | null = null;
	for (const [metric, points] of series) {
		const peak = highestPoint(points);
		if (!peak) continue;
		if (!best || peak.value > best.point.value) {
			best = { metric, point: peak };
		}
	}
	return best;
}

function criticalThresholdCrossing(points: MetricRecord[]): MetricRecord | null {
	for (let index = 1; index < points.length; index += 1) {
		const previous = points[index - 1];
		const current = points[index];
		const critical = numberValue(current.critical_threshold);
		if (critical == null) continue;
		if (previous.value < critical && current.value >= critical) return current;
	}
	return null;
}

function anomalyEndPoint(points: MetricRecord[]): MetricRecord | null {
	for (let index = 1; index < points.length; index += 1) {
		const previous = points[index - 1];
		const current = points[index];
		if (previous.value > 0 && current.value <= previous.value * 0.45) return current;
	}
	return null;
}

function majorEventBurst(events: EventRecord[]): { t: number; count: number } | null {
	const timed = events
		.filter((event): event is EventRecord & { t: number } => typeof event.t === 'number')
		.sort((left, right) => left.t - right.t);
	let best: { t: number; count: number } | null = null;
	for (let start = 0; start < timed.length; start += 1) {
		const base = timed[start];
		const window = timed.filter((event) => event.t >= base.t && event.t <= base.t + 0.4);
		if (window.length < 3) continue;
		best = {
			t: window[Math.floor(window.length / 2)]?.t ?? base.t,
			count: window.length
		};
		break;
	}
	return best;
}

function thresholdSeverity(record: MetricRecord): NarrativeMilestone['severity'] {
	const critical = numberValue(record.critical_threshold);
	const warning = numberValue(record.warning_threshold);
	if (critical != null && record.value >= critical) return 'critical';
	if (warning != null && record.value >= warning) return 'warning';
	return 'notice';
}

function topMetricDelta(
	metrics: MetricRecord[],
	selectedTime: number
): { metric: string; delta: number; severity: NarrativeCard['severity'] } | null {
	let best: { metric: string; delta: number; severity: NarrativeCard['severity'] } | null = null;
	for (const [metric, points] of metricSeries(metrics)) {
		const currentIndex = nearestPointIndex(points, selectedTime);
		if (currentIndex <= 0) continue;
		const current = points[currentIndex];
		const previous = points[currentIndex - 1];
		const delta = current.value - previous.value;
		if (!best || Math.abs(delta) > Math.abs(best.delta)) {
			best = {
				metric,
				delta,
				severity: thresholdSeverity(current)
			};
		}
	}
	return best;
}

function nearestPointIndex(points: MetricRecord[], selectedTime: number): number {
	return points.reduce<number>((nearest, point, index) => {
		if (nearest < 0) return index;
		return Math.abs(point.t - selectedTime) < Math.abs(points[nearest]!.t - selectedTime)
			? index
			: nearest;
	}, -1);
}

function milestonePriority(kind: NarrativeMilestone['kind']): number {
	switch (kind) {
		case 'event_burst':
			return 0;
		case 'threshold_crossing':
			return 1;
		case 'peak':
			return 2;
		case 'anomaly_end':
			return 3;
		default:
			return 4;
	}
}

function numberValue(value: unknown): number | null {
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
