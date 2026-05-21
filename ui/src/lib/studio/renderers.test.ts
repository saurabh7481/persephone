import { describe, expect, test } from 'vitest';

import {
	fieldCellFromPoint,
	fieldColor,
	graphHitTest,
	graphLayout,
	graphNodeColor,
	normalizeViewport
} from './renderers';
import type { SimulationFrame } from '$lib/api-client';

const fieldFrame: SimulationFrame = {
	kind: 'field',
	frame_id: 'field-a',
	t: 1,
	tick: 1,
	solver_id: 'heat#0',
	source: 'replay',
	field: 'temperature',
	shape: [2, 3],
	dtype: 'float64',
	bounds: { min: 0, max: 10 },
	units: 'K',
	visualization: { palette: 'inferno' },
	values: [0, 2, 4, 6, 8, 10]
};

const graphFrame: SimulationFrame = {
	kind: 'graph',
	frame_id: 'graph-a',
	t: 2,
	tick: 2,
	solver_id: 'sir#0',
	source: 'replay',
	nodes: [
		{ id: '0', state: 'susceptible', x: 0, y: 0 },
		{ id: '1', state: 'infected', x: 1, y: 0 },
		{ id: '2', state: 'recovered', x: 0.5, y: 1 }
	],
	edges: [
		{ source: '0', target: '1', weight: 0.25 },
		{ source: '1', target: '2', weight: 1 }
	],
	visualization: {}
};

describe('studio viewport render helpers', () => {
	test('maps field values through configured bounds and palettes', () => {
		expect(fieldColor(fieldFrame, 0, { palette: 'inferno', autoscale: false })).toBe('#1f1536');
		expect(fieldColor(fieldFrame, 10, { palette: 'inferno', autoscale: false })).toBe('#f7d13d');
		expect(fieldColor(fieldFrame, 5, { palette: 'viridis', autoscale: false })).toBe('#2aa198');
	});

	test('hit tests field cells in canvas coordinates', () => {
		const viewport = normalizeViewport(300, 200, 2);

		expect(fieldCellFromPoint(fieldFrame, viewport, 1, 1)).toMatchObject({
			row: 0,
			column: 0,
			value: 0,
			id: '0,0'
		});
		expect(fieldCellFromPoint(fieldFrame, viewport, 299, 199)).toMatchObject({
			row: 1,
			column: 2,
			value: 10,
			id: '1,2'
		});
		expect(fieldCellFromPoint(fieldFrame, viewport, 301, 120)).toBeNull();
	});

	test('lays out graph frames and preserves SIR node state styling', () => {
		const layout = graphLayout(graphFrame, normalizeViewport(240, 160, 1));

		expect(layout.nodes).toHaveLength(3);
		expect(layout.edges[1]?.width).toBeGreaterThan(layout.edges[0]?.width ?? 0);
		expect(graphNodeColor(graphFrame.nodes[0])).toBe('#2f7dd3');
		expect(graphNodeColor(graphFrame.nodes[1])).toBe('#d44f42');
		expect(graphNodeColor(graphFrame.nodes[2])).toBe('#2f9d68');
	});

	test('hit tests graph nodes by rendered radius', () => {
		const layout = graphLayout(graphFrame, normalizeViewport(240, 160, 1));
		const infected = layout.nodes.find((node) => node.id === '1');

		expect(infected).toBeDefined();
		expect(graphHitTest(layout, infected!.x, infected!.y)).toMatchObject({
			kind: 'graph-node',
			id: '1'
		});
		expect(graphHitTest(layout, 239, 159)).toBeNull();
	});
});
