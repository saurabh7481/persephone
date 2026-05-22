import type { SimulationFrame } from '$lib/api-client';
import type { StandardViewKind } from '$lib/studio/views';

export type ViewportControlModel = {
	hasControls: boolean;
	showFieldPalette: boolean;
	showFieldScale: boolean;
	showFieldOpacity: boolean;
	showGraphSearch: boolean;
	showGraphEdgeFilter: boolean;
	showGraphGrouping: boolean;
	showGraphZoom: boolean;
};

export type ViewportSupport =
	| { state: 'ready' }
	| { state: 'unsupported'; title: string; body: string };

export function resolveViewportControls(
	frame: SimulationFrame | null,
	viewKind: StandardViewKind
): ViewportControlModel {
	const isFieldHeatmap = frame?.kind === 'field' && viewKind === 'heatmap';
	const isGraphView =
		frame?.kind === 'graph' &&
		(viewKind === 'network' ||
			viewKind === 'positioned_graph' ||
			viewKind === 'map_network' ||
			viewKind === 'matrix');
	const showGraphGrouping = Boolean(
		frame?.kind === 'graph' &&
		frame.nodes.some((node) => typeof node.group === 'string' && node.group)
	);
	const showGraphZoom =
		frame?.kind === 'graph' &&
		(viewKind === 'network' || viewKind === 'positioned_graph' || viewKind === 'map_network');

	return {
		hasControls: isFieldHeatmap || isGraphView,
		showFieldPalette: isFieldHeatmap,
		showFieldScale: isFieldHeatmap,
		showFieldOpacity: isFieldHeatmap,
		showGraphSearch: isGraphView,
		showGraphEdgeFilter: isGraphView,
		showGraphGrouping,
		showGraphZoom
	};
}

export function resolveViewportSupport(
	frame: SimulationFrame | null,
	viewKind: StandardViewKind
): ViewportSupport {
	if (!frame) return { state: 'ready' };

	if (viewKind === 'heatmap') {
		if (frame.kind === 'field') return { state: 'ready' };
		return {
			state: 'unsupported',
			title: 'Heatmap unavailable for this frame',
			body: 'Select a field replay to inspect grid-based values in the heatmap viewport.'
		};
	}

	if (viewKind === 'matrix') {
		if (frame.kind === 'graph') return { state: 'ready' };
		return {
			state: 'unsupported',
			title: 'Matrix unavailable for this frame',
			body: 'Select a graph replay to compare relationships in matrix form.'
		};
	}

	if (viewKind === 'network') {
		if (frame.kind === 'graph') return { state: 'ready' };
		return {
			state: 'unsupported',
			title: 'Network unavailable for this frame',
			body: 'Select a graph replay to inspect node-link structure in the viewport.'
		};
	}

	if (viewKind === 'positioned_graph') {
		if (frame.kind === 'graph' && hasPositionedCoordinates(frame)) return { state: 'ready' };
		return {
			state: 'unsupported',
			title: 'Positioned graph unavailable for this frame',
			body: 'This graph needs explicit x/y coordinates before the positioned graph view can render.'
		};
	}

	if (viewKind === 'map_network') {
		if (frame.kind === 'graph' && hasGeographicCoordinates(frame)) return { state: 'ready' };
		return {
			state: 'unsupported',
			title: 'Map network unavailable for this frame',
			body: 'This graph needs latitude and longitude hints before the map network view can render.'
		};
	}

	return { state: 'ready' };
}

function hasGeographicCoordinates(frame: Extract<SimulationFrame, { kind: 'graph' }>): boolean {
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

function hasPositionedCoordinates(frame: Extract<SimulationFrame, { kind: 'graph' }>): boolean {
	return frame.nodes.every(
		(node) =>
			typeof node.x === 'number' &&
			Number.isFinite(node.x) &&
			typeof node.y === 'number' &&
			Number.isFinite(node.y)
	);
}
