import type { SelectedPlaybackObject } from './playback';
import type { SimulationFrame } from '$lib/api-client';

export type FieldRenderOptions = {
	palette?: string;
	autoscale?: boolean;
	min?: number;
	max?: number;
	opacity?: number;
};

export type ViewportGeometry = {
	width: number;
	height: number;
	dpr: number;
};

export type FieldCellSelection = SelectedPlaybackObject & {
	kind: 'field-cell';
	row: number;
	column: number;
	value: number | null;
};

export type GraphLayoutNode = {
	id: string;
	x: number;
	y: number;
	radius: number;
	color: string;
	source: SimulationGraphNode;
};

export type GraphLayoutEdge = {
	source: string;
	target: string;
	x1: number;
	y1: number;
	x2: number;
	y2: number;
	width: number;
	sourceRecord: SimulationGraphEdge;
};

export type GraphLayout = {
	nodes: GraphLayoutNode[];
	edges: GraphLayoutEdge[];
};

type SimulationFieldFrame = Extract<SimulationFrame, { kind: 'field' }>;
type SimulationGraphFrame = Extract<SimulationFrame, { kind: 'graph' }>;
type SimulationGraphNode = SimulationGraphFrame['nodes'][number];
type SimulationGraphEdge = SimulationGraphFrame['edges'][number];
type PaletteName = 'inferno' | 'viridis' | 'magma' | 'gray';

const PALETTES: Record<PaletteName, string[]> = {
	inferno: ['#1f1536', '#5a256e', '#ad3f5f', '#e97445', '#f7d13d'],
	viridis: ['#39215f', '#266c8e', '#2aa198', '#70bc6b', '#d6e95f'],
	magma: ['#1d1147', '#64206a', '#b53f6f', '#ee7854', '#f6df75'],
	gray: ['#172033', '#556174', '#8a96a8', '#c7d0dc', '#eef3f8']
};

export function normalizeViewport(width: number, height: number, dpr: number): ViewportGeometry {
	return {
		width: Math.max(1, Math.floor(width)),
		height: Math.max(1, Math.floor(height)),
		dpr: Math.max(1, dpr || 1)
	};
}

export function renderSimulationFrame(
	context: CanvasRenderingContext2D,
	frame: SimulationFrame,
	viewport: ViewportGeometry,
	options: FieldRenderOptions = {},
	selectedObject: SelectedPlaybackObject | null = null
) {
	context.clearRect(0, 0, viewport.width, viewport.height);
	if (frame.kind === 'field') {
		renderFieldFrame(context, frame, viewport, options, selectedObject);
		return;
	}
	renderGraphFrame(context, frame, viewport, selectedObject);
}

export function renderFieldFrame(
	context: CanvasRenderingContext2D,
	frame: SimulationFieldFrame,
	viewport: ViewportGeometry,
	options: FieldRenderOptions = {},
	selectedObject: SelectedPlaybackObject | null = null
) {
	const [rows, columns] = frame.shape;
	const values = frame.values ?? [];
	const cellWidth = viewport.width / columns;
	const cellHeight = viewport.height / rows;
	const opacity = clamp(options.opacity ?? 1, 0.1, 1);

	context.save();
	context.globalAlpha = opacity;
	for (let row = 0; row < rows; row += 1) {
		for (let column = 0; column < columns; column += 1) {
			const value = values[row * columns + column] ?? null;
			context.fillStyle = value === null ? '#101722' : fieldColor(frame, value, options);
			context.fillRect(column * cellWidth, row * cellHeight, cellWidth + 0.5, cellHeight + 0.5);
		}
	}
	context.restore();

	if (selectedObject?.kind === 'field-cell') {
		const [row, column] = selectedObject.id.split(',').map((part) => Number(part));
		if (Number.isInteger(row) && Number.isInteger(column)) {
			context.strokeStyle = '#ffffff';
			context.lineWidth = 2;
			context.strokeRect(
				column * cellWidth + 1,
				row * cellHeight + 1,
				cellWidth - 2,
				cellHeight - 2
			);
		}
	}
}

export function renderGraphFrame(
	context: CanvasRenderingContext2D,
	frame: SimulationGraphFrame,
	viewport: ViewportGeometry,
	selectedObject: SelectedPlaybackObject | null = null
) {
	const layout = graphLayout(frame, viewport);

	context.lineCap = 'round';
	for (const edge of layout.edges) {
		context.strokeStyle = 'rgba(82, 96, 116, 0.48)';
		context.lineWidth = edge.width;
		context.beginPath();
		context.moveTo(edge.x1, edge.y1);
		context.lineTo(edge.x2, edge.y2);
		context.stroke();
	}

	for (const node of layout.nodes) {
		const selected = selectedObject?.kind === 'graph-node' && selectedObject.id === node.id;
		context.beginPath();
		context.fillStyle = node.color;
		context.strokeStyle = selected ? '#ffffff' : 'rgba(16, 23, 34, 0.52)';
		context.lineWidth = selected ? 3 : 1.5;
		context.arc(node.x, node.y, selected ? node.radius + 2 : node.radius, 0, Math.PI * 2);
		context.fill();
		context.stroke();
	}
}

export function fieldColor(
	frame: SimulationFieldFrame,
	value: number,
	options: FieldRenderOptions = {}
): string {
	const bounds = fieldBounds(frame, options);
	const extent = bounds.max - bounds.min || 1;
	const normalized = clamp((value - bounds.min) / extent, 0, 1);
	const palette = paletteFor(
		options.palette ?? stringValue(frame.visualization.palette) ?? 'viridis'
	);
	return palette[Math.round(normalized * (palette.length - 1))] ?? palette[0];
}

export function fieldCellFromPoint(
	frame: SimulationFieldFrame,
	viewport: ViewportGeometry,
	x: number,
	y: number
): FieldCellSelection | null {
	if (x < 0 || y < 0 || x >= viewport.width || y >= viewport.height) return null;
	const [rows, columns] = frame.shape;
	const column = Math.min(columns - 1, Math.floor((x / viewport.width) * columns));
	const row = Math.min(rows - 1, Math.floor((y / viewport.height) * rows));
	const value = frame.values?.[row * columns + column] ?? null;
	return {
		kind: 'field-cell',
		id: `${row},${column}`,
		row,
		column,
		value
	};
}

export function graphLayout(frame: SimulationGraphFrame, viewport: ViewportGeometry): GraphLayout {
	const positionedNodes = frame.nodes.map((node, index) => ({
		node,
		index,
		x: numberValue(node.x),
		y: numberValue(node.y)
	}));
	const hasCoordinates = positionedNodes.every((node) => node.x !== null && node.y !== null);
	const padding = Math.min(36, Math.max(20, Math.min(viewport.width, viewport.height) * 0.12));
	const radius = Math.min(10, Math.max(6, Math.min(viewport.width, viewport.height) * 0.045));

	const nodes: GraphLayoutNode[] = hasCoordinates
		? layoutPositionedNodes(positionedNodes, viewport, padding, radius)
		: layoutCircularNodes(frame.nodes, viewport, padding, radius);
	const nodesById = new Map(nodes.map((node) => [node.id, node]));

	const edges = frame.edges.flatMap((edge) => {
		const source = nodesById.get(edge.source);
		const target = nodesById.get(edge.target);
		if (!source || !target) return [];
		return [
			{
				source: edge.source,
				target: edge.target,
				x1: source.x,
				y1: source.y,
				x2: target.x,
				y2: target.y,
				width: 1 + clamp(numberValue(edge.weight) ?? 0.35, 0, 1) * 3,
				sourceRecord: edge
			}
		];
	});

	return { nodes, edges };
}

export function graphNodeColor(node: SimulationGraphNode): string {
	const state = String(node.state ?? node.status ?? '').toLowerCase();
	if (state === 'susceptible') return '#2f7dd3';
	if (state === 'infected') return '#d44f42';
	if (state === 'recovered') return '#2f9d68';
	if (state === 'exposed') return '#c78a1c';
	return '#66758b';
}

export function graphHitTest(
	layout: GraphLayout,
	x: number,
	y: number
): SelectedPlaybackObject | null {
	for (let index = layout.nodes.length - 1; index >= 0; index -= 1) {
		const node = layout.nodes[index];
		const distance = Math.hypot(node.x - x, node.y - y);
		if (distance <= node.radius + 3) {
			return { kind: 'graph-node', id: node.id };
		}
	}
	return null;
}

function fieldBounds(frame: SimulationFieldFrame, options: FieldRenderOptions) {
	if (options.autoscale && frame.values?.length) {
		const finite = frame.values.filter(Number.isFinite);
		return {
			min: Math.min(...finite),
			max: Math.max(...finite)
		};
	}
	return {
		min: options.min ?? frame.bounds.min ?? 0,
		max: options.max ?? frame.bounds.max ?? 1
	};
}

function paletteFor(name: string): string[] {
	return PALETTES[paletteName(name)] ?? PALETTES.viridis;
}

function paletteName(name: string): PaletteName {
	const normalized = name.toLowerCase();
	if (normalized === 'inferno' || normalized === 'magma' || normalized === 'gray') {
		return normalized;
	}
	return 'viridis';
}

function layoutPositionedNodes(
	nodes: Array<{ node: SimulationGraphNode; index: number; x: number | null; y: number | null }>,
	viewport: ViewportGeometry,
	padding: number,
	radius: number
): GraphLayoutNode[] {
	const xs = nodes.map((node) => node.x ?? 0);
	const ys = nodes.map((node) => node.y ?? 0);
	const minX = Math.min(...xs);
	const maxX = Math.max(...xs);
	const minY = Math.min(...ys);
	const maxY = Math.max(...ys);
	const spanX = maxX - minX || 1;
	const spanY = maxY - minY || 1;

	return nodes.map(({ node, x, y }) => ({
		id: node.id,
		x: padding + (((x ?? 0) - minX) / spanX) * (viewport.width - padding * 2),
		y: padding + (((y ?? 0) - minY) / spanY) * (viewport.height - padding * 2),
		radius,
		color: graphNodeColor(node),
		source: node
	}));
}

function layoutCircularNodes(
	nodes: SimulationGraphNode[],
	viewport: ViewportGeometry,
	padding: number,
	radius: number
): GraphLayoutNode[] {
	const centerX = viewport.width / 2;
	const centerY = viewport.height / 2;
	const graphRadius = Math.max(1, Math.min(viewport.width, viewport.height) / 2 - padding);

	return nodes.map((node, index) => {
		const angle = -Math.PI / 2 + (index / Math.max(1, nodes.length)) * Math.PI * 2;
		return {
			id: node.id,
			x: centerX + Math.cos(angle) * graphRadius,
			y: centerY + Math.sin(angle) * graphRadius,
			radius,
			color: graphNodeColor(node),
			source: node
		};
	});
}

function numberValue(value: unknown): number | null {
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function stringValue(value: unknown): string | null {
	return typeof value === 'string' ? value : null;
}

function clamp(value: number, min: number, max: number): number {
	return Math.min(max, Math.max(min, value));
}
