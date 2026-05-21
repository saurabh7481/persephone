import { describe, expect, test } from 'vitest';

import {
	currentMetricCards,
	eventMarkers,
	frameTickMarkers,
	metricTimelineSeries,
	timelineDomain,
	timeFromBrush,
	timeFromPointer
} from './timeline';
import type { EventRecord, MetricRecord, SimulationFrame } from '$lib/api-client';

const metrics: MetricRecord[] = [
	{ t: 1, metric: 'metric_a', value: 17 },
	{ t: 1, metric: 'metric_b', value: 3 },
	{ t: 2, metric: 'metric_a', value: 16 },
	{ t: 2, metric: 'metric_b', value: 4 },
	{ t: 3, metric: 'metric_a', value: 14 },
	{ t: 3, metric: 'metric_b', value: 6 }
];

const events: EventRecord[] = [
	{ t: 1.5, event_type: 'infection', node: 4 },
	{ t: 2.5, event: 'recovery', node: 1 },
	{ event_type: 'missing-time' }
];

const frames: SimulationFrame[] = [
	{
		kind: 'field',
		frame_id: 'frame-a',
		t: 1,
		tick: 1,
		solver_id: 'heat#0',
		source: 'replay',
		field: 'temperature',
		shape: [1, 1],
		dtype: 'float64',
		bounds: { min: 0, max: 1 },
		units: 'temperature',
		visualization: {},
		values: [0.4]
	},
	{
		kind: 'graph',
		frame_id: 'frame-b',
		t: 3,
		tick: 3,
		solver_id: 'sir#0',
		source: 'replay',
		nodes: [{ id: '0', state: 'infected' }],
		edges: [],
		visualization: {}
	}
];

describe('metric timeline helpers', () => {
	test('builds multiple metric series and shared chart domain', () => {
		const series = metricTimelineSeries(metrics);
		const domain = timelineDomain(metrics, events, frames);

		expect(series.map((item) => item.metric)).toEqual(['metric_a', 'metric_b']);
		expect(series[0]?.points).toHaveLength(3);
		expect(domain).toEqual({ tMin: 1, tMax: 3, valueMin: 3, valueMax: 17 });
	});

	test('creates event and frame markers with labels', () => {
		expect(eventMarkers(events)).toEqual([
			{ t: 1.5, label: 'infection' },
			{ t: 2.5, label: 'recovery' }
		]);
		expect(frameTickMarkers(frames)).toEqual([
			{ t: 1, frameId: 'frame-a', tick: 1, kind: 'field' },
			{ t: 3, frameId: 'frame-b', tick: 3, kind: 'graph' }
		]);
	});

	test('maps pointer and brush coordinates into timeline time', () => {
		const domain = timelineDomain(metrics, events, frames);

		expect(timeFromPointer(150, 300, domain)).toBe(2);
		expect(timeFromBrush([75, 225], 300, domain)).toEqual({ start: 1.5, end: 2.5 });
	});

	test('summarizes metric values at the selected playback time', () => {
		expect(currentMetricCards(metrics, 2.2)).toEqual([
			{ metric: 'metric_a', value: 16, t: 2 },
			{ metric: 'metric_b', value: 4, t: 2 }
		]);
	});
});
