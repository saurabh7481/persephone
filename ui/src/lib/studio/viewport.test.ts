import { describe, expect, test } from 'vitest';

import { resolveViewportControls, resolveViewportSupport } from '$lib/studio/viewport';
import type { SimulationFrame } from '$lib/api-client';
import type { StandardViewKind } from '$lib/studio/views';

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
	visualization: { palette: 'inferno' },
	values: [0, 1, 2, 3]
};

const networkFrame: SimulationFrame = {
	kind: 'graph',
	frame_id: 'graph-a',
	t: 2,
	tick: 2,
	solver_id: 'network#0',
	source: 'replay',
	nodes: [
		{ id: 'alpha', label: 'Alpha', group: 'north' },
		{ id: 'beta', label: 'Beta', group: 'south' }
	],
	edges: [{ source: 'alpha', target: 'beta', weight: 0.8 }],
	visualization: {}
};

const positionedFrame: SimulationFrame = {
	...networkFrame,
	nodes: [
		{ id: 'alpha', label: 'Alpha', group: 'north', x: 0, y: 0 },
		{ id: 'beta', label: 'Beta', group: 'south', x: 1, y: 1 }
	]
};

const mapFrame: SimulationFrame = {
	...networkFrame,
	nodes: [
		{ id: 'alpha', label: 'Alpha', group: 'north', lat: 34.05, lon: -118.24 },
		{ id: 'beta', label: 'Beta', group: 'south', lat: 40.71, lon: -74.0 }
	],
	visualization: { coordinate_system: 'geo' }
};

describe('viewport presentation helpers', () => {
	test('shows only field controls for heatmaps', () => {
		expect(resolveViewportControls(fieldFrame, 'heatmap')).toEqual({
			hasControls: true,
			showFieldPalette: true,
			showFieldScale: true,
			showFieldOpacity: true,
			showGraphSearch: false,
			showGraphEdgeFilter: false,
			showGraphGrouping: false,
			showGraphZoom: false
		});
	});

	test('keeps graph controls relevant to the selected graph view', () => {
		expect(resolveViewportControls(networkFrame, 'network')).toEqual({
			hasControls: true,
			showFieldPalette: false,
			showFieldScale: false,
			showFieldOpacity: false,
			showGraphSearch: true,
			showGraphEdgeFilter: true,
			showGraphGrouping: true,
			showGraphZoom: true
		});

		expect(resolveViewportControls(networkFrame, 'matrix')).toEqual({
			hasControls: true,
			showFieldPalette: false,
			showFieldScale: false,
			showFieldOpacity: false,
			showGraphSearch: true,
			showGraphEdgeFilter: true,
			showGraphGrouping: true,
			showGraphZoom: false
		});
	});

	test('reports unsupported viewport states with actionable copy', () => {
		expect(resolveViewportSupport(networkFrame, 'heatmap')).toEqual({
			state: 'unsupported',
			title: 'Heatmap unavailable for this frame',
			body: 'Select a field replay to inspect grid-based values in the heatmap viewport.'
		});

		expect(resolveViewportSupport(networkFrame, 'positioned_graph')).toEqual({
			state: 'unsupported',
			title: 'Positioned graph unavailable for this frame',
			body: 'This graph needs explicit x/y coordinates before the positioned graph view can render.'
		});

		expect(resolveViewportSupport(networkFrame, 'map_network')).toEqual({
			state: 'unsupported',
			title: 'Map network unavailable for this frame',
			body: 'This graph needs latitude and longitude hints before the map network view can render.'
		});
	});

	test('treats compatible viewport states as ready', () => {
		for (const [frame, view] of [
			[fieldFrame, 'heatmap'],
			[networkFrame, 'network'],
			[positionedFrame, 'positioned_graph'],
			[mapFrame, 'map_network'],
			[networkFrame, 'matrix']
		] as Array<[SimulationFrame, StandardViewKind]>) {
			expect(resolveViewportSupport(frame, view)).toEqual({ state: 'ready' });
		}
	});
});
