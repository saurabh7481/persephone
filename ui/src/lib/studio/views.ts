import type { PluginSemantics, SimulationFrame } from '$lib/api-client';

export type StandardViewKind =
	| 'network'
	| 'positioned_graph'
	| 'map_network'
	| 'matrix'
	| 'table'
	| 'timeline'
	| 'heatmap'
	| 'hierarchy';

export type ViewSurface = 'viewport' | 'metrics' | 'table';

export type StandardViewDefinition = {
	kind: StandardViewKind;
	label: string;
	description: string;
	surface: ViewSurface;
};

export type ViewRecommendation = StandardViewDefinition & {
	reason: string;
};

export const standardViews: StandardViewDefinition[] = [
	{
		kind: 'network',
		label: 'Network',
		description: 'Topology-first graph analysis for relationship structure.',
		surface: 'viewport'
	},
	{
		kind: 'positioned_graph',
		label: 'Positioned graph',
		description: 'Graph playback using explicit x/y coordinates from the plugin.',
		surface: 'viewport'
	},
	{
		kind: 'map_network',
		label: 'Map network',
		description: 'Geographic graph playback driven by latitude and longitude hints.',
		surface: 'viewport'
	},
	{
		kind: 'matrix',
		label: 'Matrix',
		description: 'Dense graph fallback when connectivity overwhelms node-link rendering.',
		surface: 'table'
	},
	{
		kind: 'table',
		label: 'Table',
		description: 'Structured inspection fallback for plugin-defined entities and summaries.',
		surface: 'table'
	},
	{
		kind: 'timeline',
		label: 'Timeline',
		description: 'Metric and event history when trends matter more than geometry.',
		surface: 'metrics'
	},
	{
		kind: 'heatmap',
		label: 'Heatmap',
		description: 'Field-style playback when values are laid out on a fixed grid.',
		surface: 'viewport'
	},
	{
		kind: 'hierarchy',
		label: 'Hierarchy',
		description: 'Tree-style fallback for grouped or nested entity structures.',
		surface: 'table'
	}
];

export function chooseDefaultView({
	frame,
	pluginSemantics
}: {
	frame: SimulationFrame | null;
	pluginSemantics: PluginSemantics[];
}): ViewRecommendation {
	const capabilities = uniqueCapabilityKinds(pluginSemantics);
	const preferred = preferredView(pluginSemantics);
	if (preferred && capabilities.has(preferred)) {
		return recommendation(
			preferred,
			'Plugin semantics declared this as the preferred standard analysis view.'
		);
	}

	if (frame?.kind === 'graph') {
		if (hasGeographicCoordinates(frame)) {
			return recommendation('map_network', 'Graph nodes include geographic coordinates.');
		}
		if (isDenseGraph(frame)) {
			return recommendation('matrix', 'Graph density hints suggest a matrix-style fallback.');
		}
		if (hasPositionedCoordinates(frame)) {
			return recommendation('positioned_graph', 'Graph nodes provide explicit x/y coordinates.');
		}
		return recommendation('network', 'Graph playback is present without stronger spatial hints.');
	}

	if (frame?.kind === 'field') {
		return recommendation(
			'heatmap',
			'Field playback is best read through the existing heatmap viewport.'
		);
	}

	if (capabilities.has('timeline')) {
		return recommendation('timeline', 'Plugin semantics emphasize temporal inspection.');
	}
	if (capabilities.has('table')) {
		return recommendation('table', 'Plugin semantics fall back to table-oriented inspection.');
	}
	return recommendation(
		'timeline',
		'No frame or semantic preference was available, so trend analysis stays primary.'
	);
}

export function availableViews({
	frame,
	pluginSemantics
}: {
	frame: SimulationFrame | null;
	pluginSemantics: PluginSemantics[];
}): StandardViewDefinition[] {
	const kinds = uniqueCapabilityKinds(pluginSemantics);
	const recommended = chooseDefaultView({ frame, pluginSemantics });
	kinds.add(recommended.kind);
	kinds.add('timeline');
	kinds.add('table');
	if (frame?.kind === 'field') kinds.add('heatmap');
	if (frame?.kind === 'graph') {
		kinds.add('network');
		if (hasPositionedCoordinates(frame)) kinds.add('positioned_graph');
		if (hasGeographicCoordinates(frame)) kinds.add('map_network');
		if (isDenseGraph(frame)) kinds.add('matrix');
	}
	return standardViews.filter((view) => kinds.has(view.kind));
}

function preferredView(pluginSemantics: PluginSemantics[]): StandardViewKind | null {
	for (const plugin of pluginSemantics) {
		const kind = plugin.semantics.preferred_view;
		if (kind && isStandardViewKind(kind)) return kind;
	}
	return null;
}

function uniqueCapabilityKinds(pluginSemantics: PluginSemantics[]): Set<StandardViewKind> {
	const kinds = new Set<StandardViewKind>();
	for (const plugin of pluginSemantics) {
		for (const capability of plugin.semantics.view_capabilities ?? []) {
			if (isStandardViewKind(capability.kind)) kinds.add(capability.kind);
		}
	}
	return kinds;
}

function hasGeographicCoordinates(frame: Extract<SimulationFrame, { kind: 'graph' }>): boolean {
	return (
		frame.visualization.coordinate_system === 'geo' ||
		frame.nodes.some(
			(node) =>
				typeof node.lat === 'number' &&
				Number.isFinite(node.lat) &&
				typeof node.lon === 'number' &&
				Number.isFinite(node.lon)
		)
	);
}

function hasPositionedCoordinates(frame: Extract<SimulationFrame, { kind: 'graph' }>): boolean {
	return frame.nodes.some(
		(node) =>
			typeof node.x === 'number' &&
			Number.isFinite(node.x) &&
			typeof node.y === 'number' &&
			Number.isFinite(node.y)
	);
}

function isDenseGraph(frame: Extract<SimulationFrame, { kind: 'graph' }>): boolean {
	if (frame.visualization.density_hint === 'dense') return true;
	const nodeCount = frame.nodes.length || 1;
	return frame.edges.length / nodeCount >= 2;
}

function recommendation(kind: StandardViewKind, reason: string): ViewRecommendation {
	const view = standardViews.find((candidate) => candidate.kind === kind);
	if (!view) throw new Error(`Unknown standard view kind: ${kind}`);
	return { ...view, reason };
}

function isStandardViewKind(value: string): value is StandardViewKind {
	return standardViews.some((view) => view.kind === value);
}
