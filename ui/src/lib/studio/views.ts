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
	purpose: string;
	bestFit: string;
	fallback: string;
	empty: {
		title: string;
		body: string;
	};
	loading: {
		title: string;
		body: string;
	};
	help: string;
};

export type ViewRecommendation = StandardViewDefinition & {
	reason: string;
};

export const standardViews: StandardViewDefinition[] = [
	{
		kind: 'network',
		label: 'Network',
		description: 'Topology-first graph analysis for relationship structure.',
		surface: 'viewport',
		purpose: 'Show graph structure as a node-link diagram when shape and neighborhood matter most.',
		bestFit: 'Best when the graph is small enough to read as connected neighborhoods and paths.',
		fallback: 'Fallback to Matrix or Table when overlap makes relationship reading too noisy.',
		empty: {
			title: 'No network frame ready',
			body: 'Load a graph replay to inspect node-link structure in this view.'
		},
		loading: {
			title: 'Preparing network layout',
			body: 'Persephone is buffering graph frames before the network view can render.'
		},
		help: 'Use search and selection to follow neighborhoods, edges, and local hotspots.'
	},
	{
		kind: 'positioned_graph',
		label: 'Positioned graph',
		description: 'Graph playback using explicit x/y coordinates from the plugin.',
		surface: 'viewport',
		purpose:
			'Respect plugin-provided coordinates so the graph can be read in its authored spatial layout.',
		bestFit:
			'Best when node position carries meaning such as floor plans, process lanes, or designed layouts.',
		fallback:
			'Fallback to Network if the authored coordinates are sparse, unstable, or hard to compare.',
		empty: {
			title: 'No positioned graph available',
			body: 'This run needs graph nodes with explicit x/y coordinates before the positioned view can render.'
		},
		loading: {
			title: 'Loading positioned graph',
			body: 'Coordinate-aware graph playback will appear as soon as the next frame is available.'
		},
		help: 'Selection follows the authored layout, so use it when node placement is part of the story.'
	},
	{
		kind: 'map_network',
		label: 'Map network',
		description: 'Geographic graph playback driven by latitude and longitude hints.',
		surface: 'viewport',
		purpose:
			'Anchor graph playback to geography so regional clusters and long-distance links stay intuitive.',
		bestFit: 'Best when latitude/longitude hints explain how pressure or flow moves across places.',
		fallback:
			'Fallback to Positioned graph or Network when geographic coordinates are missing or unhelpful.',
		empty: {
			title: 'No geographic frame available',
			body: 'This run needs latitude and longitude hints before the map network view can render.'
		},
		loading: {
			title: 'Loading map network',
			body: 'Geographic overlays and graph playback will appear as soon as graph frames arrive.'
		},
		help: 'Compare local clusters against long-distance links, then select a node or edge for regional detail.'
	},
	{
		kind: 'matrix',
		label: 'Matrix',
		description: 'Dense graph fallback when connectivity overwhelms node-link rendering.',
		surface: 'viewport',
		purpose:
			'Compare dense relationships in a stable grid when node-link overlap hides the important structure.',
		bestFit: 'Best when the densest relationships matter more than preserving a spatial layout.',
		fallback:
			'Fallback to the table surface when you need a simpler inventory of entities before returning to Matrix.',
		empty: {
			title: 'No relationship matrix available',
			body: 'A graph frame is required before Persephone can compare connectivity in matrix form.'
		},
		loading: {
			title: 'Loading relationship matrix',
			body: 'Persephone is buffering graph frames before building the matrix surface.'
		},
		help: 'Use the matrix to spot the densest relationships first, then drill into selected rows and columns.'
	},
	{
		kind: 'table',
		label: 'Table',
		description: 'Structured inspection fallback for plugin-defined entities and summaries.',
		surface: 'table',
		purpose:
			'Turn the current frame into a browseable inventory when you need schema-aware inspection over geometry.',
		bestFit:
			'Best when labels, statuses, attributes, and grouped entities matter more than layout.',
		fallback:
			'Fallback to Hierarchy for grouped structures or back to viewport views for spatial context.',
		empty: {
			title: 'Nothing to inspect yet',
			body: 'Load a run with frame data to browse entity rows, relationships, and field cells here.'
		},
		loading: {
			title: 'Preparing table inspection',
			body: 'Persephone is waiting for frame data before building the inspection table.'
		},
		help: 'Use this view for readable lists, grouped entities, and quick selection when the viewport is too dense.'
	},
	{
		kind: 'timeline',
		label: 'Timeline',
		description: 'Metric and event history when trends matter more than geometry.',
		surface: 'metrics',
		purpose:
			'Keep trend reading front and center when the key question is how metrics and events changed over time.',
		bestFit:
			'Best when you want to align thresholds, events, and playback time around one evolving signal.',
		fallback:
			'Fallback to Heatmap, Network, or Table when a spatial frame explains the run more directly.',
		empty: {
			title: 'No timeline data yet',
			body: 'Metrics and events will populate this timeline as soon as the run emits observations.'
		},
		loading: {
			title: 'Loading timeline',
			body: 'Persephone is collecting metrics and events before the timeline can render.'
		},
		help: 'Use the trend view to scrub time, compare deltas, and line up event bursts with metric movement.'
	},
	{
		kind: 'heatmap',
		label: 'Heatmap',
		description: 'Field-style playback when values are laid out on a fixed grid.',
		surface: 'viewport',
		purpose:
			'Render field values as a grid so hotspots, diffusion, and spatial gradients stay legible.',
		bestFit:
			'Best when the simulation emits field frames whose values live on a stable row and column layout.',
		fallback:
			'Fallback to Timeline or Table when you need precise values or trend comparison over spatial texture.',
		empty: {
			title: 'No field frame available',
			body: 'Load a field-based replay to inspect a heatmap in this surface.'
		},
		loading: {
			title: 'Loading heatmap',
			body: 'Persephone is buffering field frames before the heatmap can render.'
		},
		help: 'Adjust palette, opacity, and scale when you want to compare hotspots without losing the broader field.'
	},
	{
		kind: 'hierarchy',
		label: 'Hierarchy',
		description: 'Tree-style fallback for grouped or nested entity structures.',
		surface: 'table',
		purpose:
			'Organize grouped entities into a readable hierarchy when nesting or ownership is part of the story.',
		bestFit:
			'Best when entities naturally cluster into services, teams, regions, or parent-child groupings.',
		fallback:
			'Fallback to Table when grouping is weak or when you need a flatter inventory to scan quickly.',
		empty: {
			title: 'No hierarchy to show yet',
			body: 'Load grouped graph entities before opening the hierarchy view.'
		},
		loading: {
			title: 'Preparing hierarchy',
			body: 'Persephone is collecting grouped entities before drawing the hierarchy surface.'
		},
		help: 'Use the grouped sections to compare clusters first, then inspect entities and relationships inside each branch.'
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

export function viewNarrative({
	current,
	recommended,
	locked
}: {
	current: StandardViewDefinition;
	recommended: StandardViewDefinition;
	locked: boolean;
}): { title: string; summary: string; nextStep: string } {
	const recommendedCopy =
		current.kind === recommended.kind && !locked
			? `${current.label} is recommended here because ${recommended.description
					.charAt(0)
					.toLowerCase()}${recommended.description.slice(1)}`
			: `${current.label} is currently selected to emphasize ${lowercaseLead(current.purpose)}`;
	return {
		title: `${current.label} view guide`,
		summary: recommendedCopy,
		nextStep: `Use ${current.label} when you need to ${stripLead(current.bestFit, 'Best when ')}`
	};
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

function lowercaseLead(value: string): string {
	if (!value) return value;
	return value.charAt(0).toLowerCase() + value.slice(1);
}

function stripLead(value: string, prefix: string): string {
	if (value.startsWith(prefix)) return lowercaseLead(value.slice(prefix.length));
	return lowercaseLead(value);
}
