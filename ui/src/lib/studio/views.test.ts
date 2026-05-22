import { describe, expect, test } from 'vitest';

import { availableViews, chooseDefaultView, standardViews, viewNarrative } from './views';
import type { PluginSemantics, SimulationFrame } from '$lib/api-client';

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
	bounds: { min: 0, max: 10 },
	units: 'K',
	visualization: {}
};

const positionedGraph: SimulationFrame = {
	kind: 'graph',
	frame_id: 'graph-a',
	t: 2,
	tick: 2,
	solver_id: 'graph#0',
	source: 'replay',
	nodes: [
		{ id: '0', x: 0, y: 0 },
		{ id: '1', x: 1, y: 0 }
	],
	edges: [{ source: '0', target: '1', weight: 1 }],
	visualization: {}
};

const geoGraph: SimulationFrame = {
	...positionedGraph,
	nodes: [
		{ id: '0', lat: 12.1, lon: 77.5 },
		{ id: '1', lat: 12.2, lon: 77.7 }
	],
	visualization: { coordinate_system: 'geo' }
};

const denseGraph: SimulationFrame = {
	...positionedGraph,
	nodes: Array.from({ length: 10 }, (_, index) => ({ id: String(index) })),
	edges: Array.from({ length: 30 }, (_, index) => ({
		source: String(index % 10),
		target: String((index + 1) % 10)
	})),
	visualization: { density_hint: 'dense' }
};

const pluginSemantics: PluginSemantics = {
	name: 'demo',
	version: '0.1.0',
	semantics: {
		view_capabilities: [{ kind: 'table', default: true }, { kind: 'timeline' }],
		preferred_view: 'table'
	}
};

describe('standard view selection', () => {
	test('defines the v4 registry for all standard view kinds', () => {
		expect(standardViews.map((view) => view.kind)).toEqual([
			'network',
			'positioned_graph',
			'map_network',
			'matrix',
			'table',
			'timeline',
			'heatmap',
			'hierarchy'
		]);
	});

	test('prefers plugin-declared default views when they are available', () => {
		const recommendation = chooseDefaultView({
			frame: positionedGraph,
			pluginSemantics: [pluginSemantics]
		});

		expect(recommendation.kind).toBe('table');
		expect(recommendation.surface).toBe('table');
	});

	test('adapts shared defaults across market and workflow semantic domains', () => {
		const marketRecommendation = chooseDefaultView({
			frame: denseGraph,
			pluginSemantics: [
				{
					name: 'market_stress',
					version: '0.1.0',
					semantics: {
						view_capabilities: [{ kind: 'matrix', default: true }, { kind: 'timeline' }],
						preferred_view: 'matrix'
					}
				}
			]
		});
		const workflowRecommendation = chooseDefaultView({
			frame: positionedGraph,
			pluginSemantics: [
				{
					name: 'dependency_workflow',
					version: '0.1.0',
					semantics: {
						view_capabilities: [{ kind: 'hierarchy', default: true }, { kind: 'table' }],
						preferred_view: 'hierarchy'
					}
				}
			]
		});

		expect(marketRecommendation.kind).toBe('matrix');
		expect(marketRecommendation.surface).toBe('viewport');
		expect(workflowRecommendation.kind).toBe('hierarchy');
		expect(workflowRecommendation.surface).toBe('table');
	});

	test('prefers map and positioned views when coordinate data exists', () => {
		expect(chooseDefaultView({ frame: geoGraph, pluginSemantics: [] }).kind).toBe('map_network');
		expect(chooseDefaultView({ frame: positionedGraph, pluginSemantics: [] }).kind).toBe(
			'positioned_graph'
		);
	});

	test('falls back to matrix for dense graphs and heatmap for field frames', () => {
		expect(chooseDefaultView({ frame: denseGraph, pluginSemantics: [] }).kind).toBe('matrix');
		expect(chooseDefaultView({ frame: fieldFrame, pluginSemantics: [] }).kind).toBe('heatmap');
	});

	test('provides richer purpose, fit, fallback, and state guidance for each shared view', () => {
		for (const view of standardViews) {
			expect(view.purpose.length).toBeGreaterThan(20);
			expect(view.bestFit.length).toBeGreaterThan(20);
			expect(view.fallback.length).toBeGreaterThan(20);
			expect(view.empty.title.length).toBeGreaterThan(3);
			expect(view.loading.title.length).toBeGreaterThan(3);
			expect(view.help.length).toBeGreaterThan(20);
		}
	});

	test('keeps richer view guidance attached to the capability-driven registry', () => {
		const views = availableViews({
			frame: denseGraph,
			pluginSemantics: [pluginSemantics]
		});
		const matrix = views.find((view) => view.kind === 'matrix');
		const timeline = views.find((view) => view.kind === 'timeline');

		expect(matrix).toMatchObject({
			surface: 'viewport',
			purpose: expect.stringContaining('relationship'),
			bestFit: expect.stringContaining('dense'),
			fallback: expect.stringContaining('table')
		});
		expect(timeline?.help).toContain('trend');
	});

	test('builds a user-facing explanation for why the active view is on screen', () => {
		const narrative = viewNarrative({
			current: chooseDefaultView({ frame: denseGraph, pluginSemantics: [] }),
			recommended: chooseDefaultView({ frame: denseGraph, pluginSemantics: [] }),
			locked: false
		});

		expect(narrative.title).toContain('Matrix');
		expect(narrative.summary).toContain('recommended');
		expect(narrative.nextStep).toContain('densest');
	});
});
