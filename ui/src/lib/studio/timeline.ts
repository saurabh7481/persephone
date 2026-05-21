import { extent, group, max, min, scaleLinear } from 'd3';

import type { EventRecord, MetricRecord, SimulationFrame } from '$lib/api-client';

export type TimelineDomain = {
	tMin: number;
	tMax: number;
	valueMin: number;
	valueMax: number;
};

export type MetricTimelineSeries = {
	metric: string;
	points: MetricRecord[];
};

export type EventMarker = {
	t: number;
	label: string;
};

export type FrameTickMarker = {
	t: number;
	frameId: string;
	tick: number;
	kind: SimulationFrame['kind'];
};

export type CurrentMetricCard = {
	metric: string;
	value: number;
	t: number;
};

export type BrushRange = {
	start: number;
	end: number;
};

export function metricTimelineSeries(records: MetricRecord[]): MetricTimelineSeries[] {
	return Array.from(
		group(records, (record) => record.metric),
		([metric, points]) => ({
			metric,
			points: [...points].sort((left, right) => left.t - right.t)
		})
	).filter((series) => !series.metric.startsWith('scheduler.'));
}

export function timelineDomain(
	records: MetricRecord[],
	events: EventRecord[] = [],
	frames: SimulationFrame[] = []
): TimelineDomain {
	const metricTimes = records.map((record) => record.t);
	const eventTimes = eventMarkers(events).map((event) => event.t);
	const frameTimes = frames.map((frame) => frame.t);
	const allTimes = [...metricTimes, ...eventTimes, ...frameTimes];
	const [tMin = 0, tMax = 1] = extent(allTimes);
	const values = records.map((record) => record.value);
	return {
		tMin,
		tMax: tMax === tMin ? tMin + 1 : tMax,
		valueMin: min(values) ?? 0,
		valueMax: max(values) ?? 1
	};
}

export function eventMarkers(events: EventRecord[]): EventMarker[] {
	return events
		.flatMap((event) => {
			if (typeof event.t !== 'number') return [];
			return [
				{
					t: event.t,
					label: String(event.event_type ?? event.event ?? event.type ?? 'event')
				}
			];
		})
		.sort((left, right) => left.t - right.t);
}

export function frameTickMarkers(frames: SimulationFrame[]): FrameTickMarker[] {
	return frames
		.map((frame) => ({
			t: frame.t,
			frameId: frame.frame_id,
			tick: frame.tick,
			kind: frame.kind
		}))
		.sort((left, right) => left.t - right.t || left.tick - right.tick);
}

export function timeFromPointer(x: number, width: number, domain: TimelineDomain): number {
	return xScale(width, domain).invert(clamp(x, 0, Math.max(1, width)));
}

export function timeFromBrush(
	range: [number, number],
	width: number,
	domain: TimelineDomain
): BrushRange {
	const start = timeFromPointer(Math.min(...range), width, domain);
	const end = timeFromPointer(Math.max(...range), width, domain);
	return { start, end };
}

export function currentMetricCards(
	records: MetricRecord[],
	selectedTime: number
): CurrentMetricCard[] {
	return metricTimelineSeries(records).flatMap((series) => {
		const point = nearestMetricPoint(series.points, selectedTime);
		if (!point) return [];
		return [{ metric: series.metric, value: point.value, t: point.t }];
	});
}

export function xScale(width: number, domain: TimelineDomain) {
	return scaleLinear()
		.domain([domain.tMin, domain.tMax])
		.range([0, Math.max(1, width)]);
}

export function yScale(height: number, domain: TimelineDomain) {
	const valueMax = domain.valueMax === domain.valueMin ? domain.valueMin + 1 : domain.valueMax;
	return scaleLinear()
		.domain([domain.valueMin, valueMax])
		.range([Math.max(1, height), 0])
		.nice();
}

function nearestMetricPoint(points: MetricRecord[], selectedTime: number): MetricRecord | null {
	return points.reduce<MetricRecord | null>((nearest, point) => {
		if (!nearest) return point;
		return Math.abs(point.t - selectedTime) < Math.abs(nearest.t - selectedTime) ? point : nearest;
	}, null);
}

function clamp(value: number, minValue: number, maxValue: number): number {
	return Math.min(maxValue, Math.max(minValue, value));
}
