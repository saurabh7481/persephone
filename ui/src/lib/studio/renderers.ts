import type { SelectedPlaybackObject } from './playback';
import type { SimulationFrame } from '$lib/api-client';

export type FieldRenderOptions = {
	palette?: string;
	autoscale?: boolean;
	min?: number;
	max?: number;
	opacity?: number;
};

export type GraphRenderMode = 'network' | 'positioned_graph' | 'map_network' | 'matrix';

export type GraphRenderOptions = {
	mode?: GraphRenderMode;
	search?: string;
	edgeThreshold?: number;
	aggregateGroups?: boolean;
	zoom?: number;
	panX?: number;
	panY?: number;
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
	label: string;
	group: string | null;
	highlighted: boolean;
	dimmed: boolean;
	source: SimulationGraphNode;
};

export type GraphLayoutEdge = {
	id: string;
	source: string;
	target: string;
	x1: number;
	y1: number;
	x2: number;
	y2: number;
	width: number;
	weight: number;
	edgeCount: number;
	label: string;
	highlighted: boolean;
	dimmed: boolean;
	sourceRecord: SimulationGraphEdge;
};

export type GraphMatrixCell = {
	id: string;
	source: string;
	target: string;
	x: number;
	y: number;
	size: number;
	weight: number;
	edgeCount: number;
	highlighted: boolean;
	dimmed: boolean;
	sourceRecord: SimulationGraphEdge | null;
};

export type GraphLayout = {
	mode: 'node-link' | 'matrix';
	nodes: GraphLayoutNode[];
	edges: GraphLayoutEdge[];
	matrixCells: GraphMatrixCell[];
	hiddenEdgeCount: number;
};

type SimulationFieldFrame = Extract<SimulationFrame, { kind: 'field' }>;
type SimulationGraphFrame = Extract<SimulationFrame, { kind: 'graph' }>;
type SimulationGraphNode = SimulationGraphFrame['nodes'][number];
type SimulationGraphEdge = SimulationGraphFrame['edges'][number];
type PaletteName = 'inferno' | 'viridis' | 'magma' | 'gray';
type RawGraphEdge = {
	source: string;
	target: string;
	weight: number;
	edgeCount: number;
	kind: string | null;
	directed: boolean | null;
	attrs: Record<string, unknown> | null;
	sourceRecord: SimulationGraphEdge;
};

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
	selectedObject: SelectedPlaybackObject | null = null,
	graphOptions: GraphRenderOptions = {}
) {
	context.clearRect(0, 0, viewport.width, viewport.height);
	if (frame.kind === 'field') {
		renderFieldFrame(context, frame, viewport, options, selectedObject);
		return;
	}
	renderGraphFrame(context, frame, viewport, selectedObject, graphOptions);
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
	selectedObject: SelectedPlaybackObject | null = null,
	options: GraphRenderOptions = {}
) {
	const layout = graphLayout(frame, viewport, options);
	if (layout.mode === 'matrix') {
		renderGraphMatrix(context, layout, viewport, selectedObject);
		return;
	}

	if (options.mode === 'map_network') drawMapOverlay(context, viewport);

	context.lineCap = 'round';
	for (const edge of layout.edges) {
		const selected = selectedObject?.kind === 'graph-edge' && selectedObject.id === edge.id;
		context.strokeStyle = edgeStroke(edge, selected);
		context.lineWidth = selected ? edge.width + 1.5 : edge.width;
		context.beginPath();
		context.moveTo(edge.x1, edge.y1);
		context.lineTo(edge.x2, edge.y2);
		context.stroke();
	}

	for (const node of layout.nodes) {
		const selected = selectedObject?.kind === 'graph-node' && selectedObject.id === node.id;
		context.beginPath();
		context.fillStyle = node.color;
		context.strokeStyle = selected || node.highlighted ? '#ffffff' : 'rgba(16, 23, 34, 0.52)';
		context.globalAlpha = node.dimmed ? 0.3 : 1;
		context.lineWidth = selected ? 3 : node.highlighted ? 2.5 : 1.5;
		context.arc(node.x, node.y, selected ? node.radius + 2 : node.radius, 0, Math.PI * 2);
		context.fill();
		context.stroke();
		context.globalAlpha = 1;
		if (selected || node.highlighted) {
			context.fillStyle = '#f8fafc';
			context.font = '12px sans-serif';
			context.fillText(node.label, node.x + node.radius + 4, node.y - node.radius - 2);
		}
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

export function graphLayout(
	frame: SimulationGraphFrame,
	viewport: ViewportGeometry,
	options: GraphRenderOptions = {}
): GraphLayout {
	const search = options.search?.trim().toLowerCase() ?? '';
	const aggregatedFrame = options.aggregateGroups ? aggregateGraphFrame(frame) : frame;
	const threshold = options.edgeThreshold;
	const rawEdges = toRawEdges(aggregatedFrame.edges).filter(
		(edge) => edge.weight >= (threshold ?? -Infinity)
	);
	const hiddenEdgeCount = aggregatedFrame.edges.length - rawEdges.length;
	const graphMode = resolveGraphMode(aggregatedFrame, options.mode);
	const padding =
		graphMode === 'matrix'
			? 42
			: Math.min(36, Math.max(20, Math.min(viewport.width, viewport.height) * 0.12));
	const positionedNodes = positionedGraphNodes(aggregatedFrame, graphMode);
	const radiusRange = nodeRadiusScale(
		positionedNodes.map(({ node }) => firstNumericMetricValue(node))
	);
	const baseNodes =
		graphMode === 'matrix'
			? positionedNodes
					.map(({ node }) => node)
					.sort((left, right) => nodeLabel(left).localeCompare(nodeLabel(right)))
					.map((node, index, nodes) => {
						const size = Math.max(1, Math.min(viewport.width, viewport.height) - padding * 2);
						const step = size / Math.max(nodes.length, 1);
						return {
							id: node.id,
							x: padding + step * index + step / 2,
							y: padding + step * index + step / 2,
							radius: radiusForMetric(firstNumericMetricValue(node), radiusRange),
							color: graphNodeColor(node),
							label: nodeLabel(node),
							group: stringValue(node.group),
							highlighted: nodeMatchesSearch(node, search),
							dimmed: search.length > 0 && !nodeMatchesSearch(node, search),
							source: node
						} satisfies GraphLayoutNode;
					})
			: layoutSpatialNodes(positionedNodes, viewport, padding, radiusRange, options);
	const nodesById = new Map(baseNodes.map((node) => [node.id, node]));
	const edges = rawEdges.flatMap((edge) => {
		const source = nodesById.get(edge.source);
		const target = nodesById.get(edge.target);
		if (!source || !target || source.id === target.id) return [];
		const highlighted =
			edgeMatchesSearch(edge, search) || Boolean(source.highlighted) || Boolean(target.highlighted);
		return [
			{
				id: edgeSelectionId(edge.source, edge.target),
				source: edge.source,
				target: edge.target,
				x1: source.x,
				y1: source.y,
				x2: target.x,
				y2: target.y,
				width: 1 + clamp(edge.weight, 0, 2) * 2,
				weight: edge.weight,
				edgeCount: edge.edgeCount,
				label: `${source.label} -> ${target.label}`,
				highlighted,
				dimmed: search.length > 0 && !highlighted,
				sourceRecord: edge.sourceRecord
			} satisfies GraphLayoutEdge
		];
	});

	if (graphMode === 'matrix') {
		const matrixCells = buildMatrixCells(baseNodes, edges, viewport, padding);
		return {
			mode: 'matrix',
			nodes: baseNodes,
			edges,
			matrixCells,
			hiddenEdgeCount
		};
	}

	return {
		mode: 'node-link',
		nodes: baseNodes,
		edges,
		matrixCells: [],
		hiddenEdgeCount
	};
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
	if (layout.mode === 'matrix') {
		for (let index = layout.matrixCells.length - 1; index >= 0; index -= 1) {
			const cell = layout.matrixCells[index];
			if (
				x >= cell.x &&
				x <= cell.x + cell.size &&
				y >= cell.y &&
				y <= cell.y + cell.size &&
				cell.weight > 0
			) {
				return { kind: 'graph-edge', id: cell.id };
			}
		}
		return null;
	}

	for (let index = layout.nodes.length - 1; index >= 0; index -= 1) {
		const node = layout.nodes[index];
		const distance = Math.hypot(node.x - x, node.y - y);
		if (distance <= node.radius + 3) {
			return { kind: 'graph-node', id: node.id };
		}
	}

	for (let index = layout.edges.length - 1; index >= 0; index -= 1) {
		const edge = layout.edges[index];
		if (
			distanceToSegment(x, y, edge.x1, edge.y1, edge.x2, edge.y2) <= Math.max(5, edge.width + 2)
		) {
			return { kind: 'graph-edge', id: edge.id };
		}
	}
	return null;
}

export function describeGraphObject(
	layout: GraphLayout,
	object: SelectedPlaybackObject | null
): string {
	if (!object) return '';
	if (object.kind === 'graph-node') {
		const node = layout.nodes.find((candidate) => candidate.id === object.id);
		return node ? `${node.label} · ${node.group ?? 'node'}` : object.id;
	}
	if (object.kind === 'graph-edge') {
		const edge = layout.edges.find((candidate) => candidate.id === object.id);
		return edge ? `${edge.label} · weight ${edge.weight.toFixed(2)}` : object.id;
	}
	return object.id;
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

function layoutSpatialNodes(
	nodes: Array<{
		node: SimulationGraphNode;
		x: number | null;
		y: number | null;
	}>,
	viewport: ViewportGeometry,
	padding: number,
	radiusRange: { min: number; max: number; low: number; high: number },
	options: GraphRenderOptions
): GraphLayoutNode[] {
	const xs = nodes.map((node) => node.x ?? 0);
	const ys = nodes.map((node) => node.y ?? 0);
	const minX = Math.min(...xs);
	const maxX = Math.max(...xs);
	const minY = Math.min(...ys);
	const maxY = Math.max(...ys);
	const spanX = maxX - minX || 1;
	const spanY = maxY - minY || 1;
	const zoom = clamp(options.zoom ?? 1, 0.4, 6);
	const panX = options.panX ?? 0;
	const panY = options.panY ?? 0;
	const search = options.search?.trim().toLowerCase() ?? '';

	return nodes.map(({ node, x, y }) => {
		const rawX = padding + (((x ?? 0) - minX) / spanX) * (viewport.width - padding * 2);
		const rawY = padding + (((y ?? 0) - minY) / spanY) * (viewport.height - padding * 2);
		const transformed = applyGraphTransform(rawX, rawY, viewport, zoom, panX, panY);
		const highlighted = nodeMatchesSearch(node, search);
		return {
			id: node.id,
			x: transformed.x,
			y: transformed.y,
			radius: radiusForMetric(firstNumericMetricValue(node), radiusRange),
			color: graphNodeColor(node),
			label: nodeLabel(node),
			group: stringValue(node.group),
			highlighted,
			dimmed: search.length > 0 && !highlighted,
			source: node
		} satisfies GraphLayoutNode;
	});
}

function positionedGraphNodes(
	frame: SimulationGraphFrame,
	mode: GraphRenderMode
): Array<{ node: SimulationGraphNode; x: number | null; y: number | null }> {
	if (mode === 'map_network') {
		return frame.nodes.map((node) => ({
			node,
			x: numberValue(node.lon),
			y: numberValue(node.lat)
		}));
	}
	if (mode === 'positioned_graph') {
		return frame.nodes.map((node) => ({
			node,
			x: numberValue(node.x),
			y: numberValue(node.y)
		}));
	}
	return [...frame.nodes]
		.sort((left, right) => left.id.localeCompare(right.id))
		.map((node, index, nodes) => {
			const angle = -Math.PI / 2 + (index / Math.max(1, nodes.length)) * Math.PI * 2;
			return {
				node,
				x: Math.cos(angle),
				y: Math.sin(angle)
			};
		});
}

function resolveGraphMode(
	frame: SimulationGraphFrame,
	requested: GraphRenderMode | undefined
): GraphRenderMode {
	if (requested) return requested;
	if (hasGeographicCoordinates(frame)) return 'map_network';
	if (hasPositionedCoordinates(frame)) return 'positioned_graph';
	return 'network';
}

function hasGeographicCoordinates(frame: SimulationGraphFrame): boolean {
	return (
		frame.visualization.coordinate_system === 'geo' ||
		frame.nodes.every(
			(node) =>
				typeof node.lat === 'number' &&
				Number.isFinite(node.lat) &&
				typeof node.lon === 'number' &&
				Number.isFinite(node.lon)
		)
	);
}

function hasPositionedCoordinates(frame: SimulationGraphFrame): boolean {
	return frame.nodes.every(
		(node) =>
			typeof node.x === 'number' &&
			Number.isFinite(node.x) &&
			typeof node.y === 'number' &&
			Number.isFinite(node.y)
	);
}

function toRawEdges(edges: SimulationGraphEdge[]): RawGraphEdge[] {
	return edges.map((edge) => ({
		source: edge.source,
		target: edge.target,
		weight: clamp(numberValue(edge.weight) ?? 0.35, 0, 2),
		edgeCount:
			numberValue(recordValue(edge.attrs)?.edge_count) ??
			numberValue(recordValue(edge.attrs)?.edgeCount) ??
			1,
		kind: stringValue(edge.kind),
		directed: typeof edge.directed === 'boolean' ? edge.directed : null,
		attrs: recordValue(edge.attrs),
		sourceRecord: edge
	}));
}

function aggregateGraphFrame(frame: SimulationGraphFrame): SimulationGraphFrame {
	const groups = new Map<string, SimulationGraphNode[]>();
	for (const node of frame.nodes) {
		const group = stringValue(node.group) ?? node.id;
		const members = groups.get(group) ?? [];
		members.push(node);
		groups.set(group, members);
	}
	if (groups.size === frame.nodes.length) return frame;

	const nodes = Array.from(groups, ([group, members]) => ({
		id: group,
		label: group,
		group,
		metrics: aggregateMetrics(members),
		attrs: { member_count: members.length }
	}));
	const nodeGroup = new Map(
		frame.nodes.map((node) => [node.id, stringValue(node.group) ?? node.id])
	);
	const edgesByKey = new Map<string, RawGraphEdge>();
	for (const edge of toRawEdges(frame.edges)) {
		const sourceGroup = nodeGroup.get(edge.source) ?? edge.source;
		const targetGroup = nodeGroup.get(edge.target) ?? edge.target;
		const key = edgeSelectionId(sourceGroup, targetGroup);
		const current = edgesByKey.get(key);
		if (!current) {
			edgesByKey.set(key, { ...edge, source: sourceGroup, target: targetGroup });
			continue;
		}
		current.weight += edge.weight;
		current.edgeCount += 1;
	}

	return {
		...frame,
		nodes,
		edges: Array.from(edgesByKey.values()).map((edge) => ({
			source: edge.source,
			target: edge.target,
			weight: edge.weight,
			kind: edge.kind,
			directed: edge.directed,
			attrs: {
				...(edge.attrs ?? {}),
				edge_count: edge.edgeCount
			}
		}))
	};
}

function aggregateMetrics(nodes: SimulationGraphNode[]): Record<string, number> | null {
	const totals = new Map<string, number>();
	for (const node of nodes) {
		for (const [metric, value] of Object.entries(node.metrics ?? {})) {
			if (typeof value !== 'number' || !Number.isFinite(value)) continue;
			totals.set(metric, (totals.get(metric) ?? 0) + value);
		}
	}
	return totals.size ? Object.fromEntries(totals) : null;
}

function buildMatrixCells(
	nodes: GraphLayoutNode[],
	edges: GraphLayoutEdge[],
	viewport: ViewportGeometry,
	padding: number
): GraphMatrixCell[] {
	const size = Math.max(1, Math.min(viewport.width, viewport.height) - padding * 2);
	const step = size / Math.max(nodes.length, 1);
	const edgeIndex = new Map(edges.map((edge) => [edge.id, edge]));
	return nodes.flatMap((sourceNode, row) =>
		nodes.map((targetNode, column) => {
			const edge = edgeIndex.get(edgeSelectionId(sourceNode.id, targetNode.id)) ?? null;
			return {
				id: edgeSelectionId(sourceNode.id, targetNode.id),
				source: sourceNode.id,
				target: targetNode.id,
				x: padding + column * step,
				y: padding + row * step,
				size: step,
				weight: edge?.weight ?? 0,
				edgeCount: edge?.edgeCount ?? 0,
				highlighted: edge?.highlighted ?? false,
				dimmed: edge?.dimmed ?? false,
				sourceRecord: edge?.sourceRecord ?? null
			} satisfies GraphMatrixCell;
		})
	);
}

function renderGraphMatrix(
	context: CanvasRenderingContext2D,
	layout: GraphLayout,
	viewport: ViewportGeometry,
	selectedObject: SelectedPlaybackObject | null
) {
	const maxWeight = Math.max(
		1,
		...layout.matrixCells.map((cell) => cell.weight),
		...layout.edges.map((edge) => edge.weight)
	);
	context.fillStyle = '#0f172a';
	context.fillRect(0, 0, viewport.width, viewport.height);
	for (const cell of layout.matrixCells) {
		const intensity = cell.weight / maxWeight;
		context.fillStyle =
			cell.weight === 0
				? 'rgba(51, 65, 85, 0.35)'
				: `rgba(47, 125, 211, ${0.25 + intensity * 0.7})`;
		context.globalAlpha = cell.dimmed ? 0.18 : 1;
		context.fillRect(cell.x, cell.y, cell.size - 1, cell.size - 1);
		context.globalAlpha = 1;
		if (selectedObject?.kind === 'graph-edge' && selectedObject.id === cell.id) {
			context.strokeStyle = '#f8fafc';
			context.lineWidth = 2;
			context.strokeRect(cell.x + 1, cell.y + 1, cell.size - 3, cell.size - 3);
		}
	}
	for (const node of layout.nodes) {
		context.fillStyle = '#cbd5e1';
		context.font = '11px sans-serif';
		context.fillText(node.label, node.x - 12, 18);
		context.save();
		context.translate(14, node.y + 12);
		context.rotate(-Math.PI / 2);
		context.fillText(node.label, 0, 0);
		context.restore();
	}
}

function drawMapOverlay(context: CanvasRenderingContext2D, viewport: ViewportGeometry) {
	context.save();
	context.strokeStyle = 'rgba(148, 163, 184, 0.18)';
	context.lineWidth = 1;
	for (let index = 1; index < 4; index += 1) {
		const x = (viewport.width / 4) * index;
		const y = (viewport.height / 4) * index;
		context.beginPath();
		context.moveTo(x, 0);
		context.lineTo(x, viewport.height);
		context.stroke();
		context.beginPath();
		context.moveTo(0, y);
		context.lineTo(viewport.width, y);
		context.stroke();
	}
	context.restore();
}

function edgeStroke(edge: GraphLayoutEdge, selected: boolean): string {
	if (selected) return 'rgba(248, 250, 252, 0.96)';
	if (edge.highlighted) return 'rgba(125, 211, 252, 0.86)';
	if (edge.dimmed) return 'rgba(82, 96, 116, 0.16)';
	return `rgba(82, 96, 116, ${clamp(0.22 + edge.weight * 0.18, 0.22, 0.7)})`;
}

function applyGraphTransform(
	x: number,
	y: number,
	viewport: ViewportGeometry,
	zoom: number,
	panX: number,
	panY: number
): { x: number; y: number } {
	const centerX = viewport.width / 2;
	const centerY = viewport.height / 2;
	return {
		x: centerX + (x - centerX) * zoom + panX,
		y: centerY + (y - centerY) * zoom + panY
	};
}

function nodeRadiusScale(values: Array<number | null>): {
	min: number;
	max: number;
	low: number;
	high: number;
} {
	const finite = values.filter(
		(value): value is number => typeof value === 'number' && Number.isFinite(value)
	);
	return {
		min: finite.length ? Math.min(...finite) : 0,
		max: finite.length ? Math.max(...finite) : 1,
		low: 6,
		high: 13
	};
}

function radiusForMetric(
	value: number | null,
	range: { min: number; max: number; low: number; high: number }
): number {
	if (value === null) return 8;
	const span = range.max - range.min || 1;
	return range.low + ((value - range.min) / span) * (range.high - range.low);
}

function firstNumericMetricValue(node: SimulationGraphNode): number | null {
	for (const value of Object.values(node.metrics ?? {})) {
		if (typeof value === 'number' && Number.isFinite(value)) return value;
	}
	return null;
}

function nodeMatchesSearch(node: SimulationGraphNode, search: string): boolean {
	if (!search) return false;
	return [node.id, node.label, node.group, node.state, node.status]
		.filter((value): value is string => typeof value === 'string')
		.some((value) => value.toLowerCase().includes(search));
}

function edgeMatchesSearch(edge: RawGraphEdge, search: string): boolean {
	if (!search) return false;
	return `${edge.source} ${edge.target}`.toLowerCase().includes(search);
}

function nodeLabel(node: SimulationGraphNode): string {
	return stringValue(node.label) ?? node.id;
}

function edgeSelectionId(source: string, target: string): string {
	return `${source}->${target}`;
}

function distanceToSegment(
	x: number,
	y: number,
	x1: number,
	y1: number,
	x2: number,
	y2: number
): number {
	const dx = x2 - x1;
	const dy = y2 - y1;
	if (dx === 0 && dy === 0) return Math.hypot(x - x1, y - y1);
	const t = clamp(((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy), 0, 1);
	const px = x1 + t * dx;
	const py = y1 + t * dy;
	return Math.hypot(x - px, y - py);
}

function numberValue(value: unknown): number | null {
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function stringValue(value: unknown): string | null {
	return typeof value === 'string' ? value : null;
}

function recordValue(value: unknown): Record<string, unknown> | null {
	return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function clamp(value: number, min: number, max: number): number {
	return Math.min(max, Math.max(min, value));
}
