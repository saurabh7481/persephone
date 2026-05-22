import { describe, expect, test } from 'vitest';

import {
	artifactSummaries,
	browseFrameEntities,
	fieldCellInspection,
	graphEdgeInspection,
	graphNodeInspection,
	runInspection
} from './inspector';
import type {
	EventRecord,
	ExplanationResponse,
	MetricRecord,
	PluginSemantics,
	RunSummary,
	SimulationFrame
} from '$lib/api-client';

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
		{
			id: '0',
			label: 'Alpha county',
			group: 'north',
			state: 'susceptible',
			metrics: { load: 0.2 },
			attrs: { population: 1200 }
		},
		{
			id: '1',
			label: 'Bravo county',
			group: 'south',
			state: 'infected',
			metrics: { load: 0.8 },
			attrs: { population: 950 }
		}
	],
	edges: [{ source: '0', target: '1', weight: 0.7, kind: 'travel', directed: true }],
	visualization: { selection_schema: { type: 'node', entity_type: 'county' } }
};

const metrics: MetricRecord[] = [{ t: 1, metric: 'temperature.mean', value: 0.25 }];
const events: EventRecord[] = [
	{ t: 2, event_type: 'infection', node: '1' },
	{ t: 2.5, event_type: 'travel_alert', source: '0', target: '1' }
];
const pluginSemantics: PluginSemantics[] = [
	{
		name: 'sir_epidemic',
		version: '0.1.0',
		semantics: {
			default_entity_type: 'county',
			entity_schemas: {
				county: [
					{ name: 'label', label: 'County', type: 'string' },
					{ name: 'population', label: 'Population', type: 'integer' }
				]
			},
			state_schema: {
				infected: {
					name: 'infected',
					label: 'Infected',
					kind: 'categorical',
					description: 'Actively infectious county'
				}
			},
			metric_schema: {
				load: {
					name: 'load',
					label: 'Transmission load',
					unit: 'idx'
				}
			},
			event_schema: {
				infection: { name: 'infection', label: 'Infection event' },
				travel_alert: { name: 'travel_alert', label: 'Travel alert' }
			}
		}
	}
];
const selectionExplanation: ExplanationResponse = {
	run_id: 'run-a',
	scope: 'selection',
	selection_id: '1',
	available: true,
	interpretation: {
		run_id: 'run-a',
		scope: 'selection',
		t: 2,
		tick: 2,
		frame_id: 'graph-a',
		selection_id: '1',
		mode_requested: 'rules_only',
		mode_applied: 'rules_only',
		label: 'Bravo county',
		cached: false,
		facts: [
			{
				kind: 'selection',
				title: 'County under pressure',
				summary: 'Bravo county now has the highest transmission load.',
				severity: 'warning',
				related_ids: ['1'],
				t: 2,
				evidence: [{ label: 'load', value: 0.8, unit: 'idx' }]
			}
		],
		summary: {
			title: 'Bravo county under pressure',
			summary: 'Transmission load rose sharply in the selected county.',
			severity: 'warning',
			fact_count: 1,
			evidence: [{ label: 'load', value: 0.8, unit: 'idx' }]
		}
	}
};

describe('studio inspector helpers', () => {
	test('inspects selected field cells with frame metadata', () => {
		expect(fieldCellInspection(fieldFrame, '1,0')).toEqual({
			id: '1,0',
			row: 1,
			column: 0,
			value: 0.3,
			units: 'K',
			field: 'temperature',
			label: 'temperature[1,0]',
			dtype: 'float64',
			shape: [2, 2],
			frameId: 'field-a',
			source: 'replay'
		});
	});

	test('inspects graph nodes with schema metadata, metrics, events, and explanation facts', () => {
		expect(
			graphNodeInspection(graphFrame, '1', events, pluginSemantics, selectionExplanation)
		).toMatchObject({
			id: '1',
			label: 'Bravo county',
			state: 'Infected',
			group: 'south',
			entityType: 'county',
			degree: 1,
			events: [{ t: 2, event_type: 'infection', node: '1' }],
			metrics: [{ label: 'Transmission load', value: '0.8 idx' }],
			fields: [
				{ label: 'County', value: 'Bravo county' },
				{ label: 'Population', value: '950' }
			],
			facts: [{ title: 'County under pressure' }]
		});
	});

	test('inspects graph edges as first-class relationships', () => {
		expect(graphEdgeInspection(graphFrame, '0->1', events, pluginSemantics)).toMatchObject({
			id: '0->1',
			label: 'Alpha county -> Bravo county',
			kind: 'travel',
			directed: true,
			weight: 0.7,
			events: [{ t: 2.5, event_type: 'travel_alert', source: '0', target: '1' }]
		});
	});

	test('humanizes fallback graph metric labels when semantics are missing', () => {
		const withoutSemantics = graphNodeInspection(graphFrame, '1', events, [], selectionExplanation);

		expect(withoutSemantics?.metrics).toEqual([{ label: 'Load', value: '0.8' }]);
	});

	test('builds browseable entity tables for graph and field frames', () => {
		expect(browseFrameEntities(graphFrame, pluginSemantics)).toMatchObject({
			mode: 'grouped',
			groups: [
				{ id: 'north', rows: [{ id: '0', label: 'Alpha county' }] },
				{ id: 'south', rows: [{ id: '1', label: 'Bravo county' }] }
			]
		});
		const fieldRows = browseFrameEntities(fieldFrame, pluginSemantics);
		expect(fieldRows.mode).toBe('table');
		if (fieldRows.mode === 'table') {
			expect(fieldRows.rows).toEqual(
				expect.arrayContaining([
					expect.objectContaining({ id: '1,1', label: 'temperature[1,1]', value: '0.4 K' }),
					expect.objectContaining({ id: '1,0', label: 'temperature[1,0]', value: '0.3 K' })
				])
			);
		}
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
			{ kind: 'events', label: 'Events', count: 2, href: '/runs/run-a/export?format=csv' },
			{ kind: 'frames', label: 'Frames', count: 2, href: '/runs/run-a/frames' },
			{ kind: 'fields', label: 'Field frames', count: 1, href: '/runs/run-a/fields' },
			{ kind: 'manifest', label: 'Run manifest', count: 1, href: '/runs/run-a' }
		]);
	});
});
