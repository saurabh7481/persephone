import { describe, expect, test } from 'vitest';

import {
	artifactSummaries,
	fieldCellInspection,
	graphNodeInspection,
	runInspection
} from './inspector';
import type { EventRecord, MetricRecord, RunSummary, SimulationFrame } from '$lib/api-client';

const run: RunSummary = {
	run_id: 'run-a',
	name: 'Baseline',
	status: 'completed',
	started_at: '2026-05-19T00:00:00Z',
	final_time: 2,
	plugins: ['sir_epidemic'],
	config_hash: 'abc123',
	artifact_path: 'runs/run-a',
	error_message: null
};

const fieldFrame: SimulationFrame = {
	kind: 'field',
	frame_id: 'field-a',
	t: 1,
	tick: 1,
	solver_id: 'heat#0',
	source: 'replay',
	field: 'temperature',
	shape: [2, 2],
	dtype: 'float64',
	bounds: { min: 0, max: 1 },
	units: 'K',
	visualization: {},
	values: [0.1, 0.2, 0.3, 0.4]
};

const graphFrame: SimulationFrame = {
	kind: 'graph',
	frame_id: 'graph-a',
	t: 2,
	tick: 2,
	solver_id: 'sir#0',
	source: 'replay',
	nodes: [
		{ id: '0', state: 'susceptible' },
		{ id: '1', state: 'infected' }
	],
	edges: [{ source: '0', target: '1', weight: 0.7 }],
	visualization: {}
};

const metrics: MetricRecord[] = [{ t: 1, metric: 'temperature.mean', value: 0.25 }];
const events: EventRecord[] = [{ t: 2, event_type: 'infection', node: '1' }];

describe('studio inspector helpers', () => {
	test('inspects selected field cells with frame metadata', () => {
		expect(fieldCellInspection(fieldFrame, '1,0')).toEqual({
			id: '1,0',
			row: 1,
			column: 0,
			value: 0.3,
			units: 'K',
			field: 'temperature',
			dtype: 'float64',
			shape: [2, 2],
			frameId: 'field-a',
			source: 'replay'
		});
	});

	test('inspects graph nodes with degree and event history', () => {
		expect(graphNodeInspection(graphFrame, '1', events)).toMatchObject({
			id: '1',
			state: 'infected',
			degree: 1,
			events: [{ t: 2, event_type: 'infection', node: '1' }]
		});
	});

	test('summarizes run and artifact entries', () => {
		expect(runInspection(run)).toMatchObject({
			runId: 'run-a',
			status: 'completed',
			plugins: 'sir_epidemic',
			runtimeBackend: 'Python',
			configHash: 'abc123'
		});
		expect(artifactSummaries(run, metrics, events, [fieldFrame, graphFrame])).toEqual([
			{ kind: 'metrics', label: 'Metrics', count: 1, href: '/runs/run-a/export?format=csv' },
			{ kind: 'events', label: 'Events', count: 1, href: '/runs/run-a/export?format=csv' },
			{ kind: 'frames', label: 'Frames', count: 2, href: '/runs/run-a/frames' },
			{ kind: 'fields', label: 'Field frames', count: 1, href: '/runs/run-a/fields' },
			{ kind: 'manifest', label: 'Run manifest', count: 1, href: '/runs/run-a' }
		]);
	});
});
