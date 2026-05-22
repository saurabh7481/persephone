import type {
	EntityField,
	EventDefinition,
	EventRecord,
	ExplanationFact,
	ExplanationResponse,
	MetricDefinition,
	PluginSemantics,
	RunSummary,
	SimulationFrame,
	StateDefinition
} from '$lib/api-client';

type SimulationGraphNode = Extract<SimulationFrame, { kind: 'graph' }>['nodes'][number];

export type FieldCellInspection = {
	id: string;
	row: number;
	column: number;
	value: number | null;
	units: string;
	field: string;
	label: string;
	dtype: string;
	shape: [number, number];
	frameId: string;
	source: string;
};

export type InspectionField = {
	label: string;
	value: string;
};

export type InspectionMetric = {
	label: string;
	value: string;
};

export type GraphNodeInspection = {
	id: string;
	label: string;
	entityType: string | null;
	state: string;
	stateDescription: string | null;
	group: string | null;
	degree: number;
	metrics: InspectionMetric[];
	fields: InspectionField[];
	events: EventRecord[];
	facts: ExplanationFact[];
	node: Record<string, unknown> & { id: string };
};

export type GraphEdgeInspection = {
	id: string;
	label: string;
	kind: string;
	directed: boolean;
	weight: number | null;
	events: EventRecord[];
	fields: InspectionField[];
	edge: Record<string, unknown> & { source: string; target: string };
};

export type BrowseFrameRow = {
	id: string;
	kind: 'graph-node' | 'graph-edge' | 'field-cell';
	label: string;
	value: string;
	description?: string | null;
};

export type BrowseFrameGroup = {
	id: string;
	label: string;
	rows: BrowseFrameRow[];
};

export type BrowseFrameEntitiesResult =
	| {
			mode: 'table';
			rows: BrowseFrameRow[];
	  }
	| {
			mode: 'grouped';
			groups: BrowseFrameGroup[];
			relationshipRows: BrowseFrameRow[];
	  };

export type RunInspection = {
	runId: string;
	status: RunSummary['status'];
	plugins: string;
	pluginVersions: string;
	runtimeBackend: string;
	configHash: string;
	seedPlan: string;
	artifactPath: string;
	startedAt: string;
	finalTime: number;
};

export type ArtifactSummary = {
	kind: 'metrics' | 'events' | 'frames' | 'fields' | 'manifest';
	label: string;
	count: number;
	href: string;
};

export function fieldCellInspection(
	frame: SimulationFrame | null,
	cellId: string | null
): FieldCellInspection | null {
	if (!frame || frame.kind !== 'field' || !cellId) return null;
	const [row, column] = cellId.split(',').map((part) => Number(part));
	if (!Number.isInteger(row) || !Number.isInteger(column)) return null;
	const [, columns] = frame.shape;
	return {
		id: cellId,
		row,
		column,
		value: frame.values?.[row * columns + column] ?? null,
		units: frame.units,
		field: frame.field,
		label: `${frame.field}[${row},${column}]`,
		dtype: frame.dtype,
		shape: frame.shape,
		frameId: frame.frame_id,
		source: frame.source
	};
}

export function graphNodeInspection(
	frame: SimulationFrame | null,
	nodeId: string | null,
	events: EventRecord[],
	pluginSemantics: PluginSemantics[] = [],
	selectionExplanation: ExplanationResponse | null = null
): GraphNodeInspection | null {
	if (!frame || frame.kind !== 'graph' || !nodeId) return null;
	const node = frame.nodes.find((candidate) => candidate.id === nodeId);
	if (!node) return null;
	const degree = frame.edges.filter(
		(edge) => edge.source === nodeId || edge.target === nodeId
	).length;
	const entityType = graphEntityType(frame, pluginSemantics);
	const eventSchema = eventDefinitions(pluginSemantics);
	const state = stateLabel(node.state ?? node.status, pluginSemantics);
	return {
		id: node.id,
		label: stringValue(node.label) ?? node.id,
		entityType,
		state: state.label,
		stateDescription: state.description,
		group: stringValue(node.group),
		degree,
		metrics: nodeMetrics(node, pluginSemantics),
		fields: entitySchemaFields(node, entityType, pluginSemantics),
		events: events.filter((event) => eventMatchesNode(event, nodeId)),
		facts: relatedFacts(selectionExplanation),
		node,
		...(eventSchema.size ? {} : {})
	};
}

export function graphEdgeInspection(
	frame: SimulationFrame | null,
	edgeId: string | null,
	events: EventRecord[],
	pluginSemantics: PluginSemantics[] = []
): GraphEdgeInspection | null {
	if (!frame || frame.kind !== 'graph' || !edgeId) return null;
	const [sourceId, targetId] = edgeId.split('->');
	const edge = frame.edges.find(
		(candidate) => candidate.source === sourceId && candidate.target === targetId
	);
	if (!edge) return null;
	const source = frame.nodes.find((candidate) => candidate.id === edge.source);
	const target = frame.nodes.find((candidate) => candidate.id === edge.target);
	const eventSchema = eventDefinitions(pluginSemantics);
	return {
		id: edgeId,
		label: `${stringValue(source?.label) ?? edge.source} -> ${stringValue(target?.label) ?? edge.target}`,
		kind: labelForEventOrKind(stringValue(edge.kind), eventSchema) ?? 'relationship',
		directed: Boolean(edge.directed),
		weight: numberValue(edge.weight),
		events: events.filter((event) => eventMatchesEdge(event, edge.source, edge.target)),
		fields: edgeFields(edge),
		edge
	};
}

export function browseFrameEntities(
	frame: SimulationFrame | null,
	pluginSemantics: PluginSemantics[] = []
): BrowseFrameEntitiesResult {
	if (!frame) return { mode: 'table', rows: [] };
	if (frame.kind === 'field') {
		return {
			mode: 'table',
			rows: fieldRows(frame)
		};
	}

	const grouped = groupGraphRows(frame, pluginSemantics);
	if (grouped.length) {
		return {
			mode: 'grouped',
			groups: grouped,
			relationshipRows: frame.edges.map((edge) => ({
				id: `${edge.source}->${edge.target}`,
				kind: 'graph-edge',
				label: `${graphLabel(frame, edge.source)} -> ${graphLabel(frame, edge.target)}`,
				value: edge.kind ? String(edge.kind) : edge.weight == null ? 'relationship' : `${edge.weight}`,
				description: edge.directed ? 'directed' : null
			}))
		};
	}

	return {
		mode: 'table',
		rows: frame.nodes.map((node) => ({
			id: node.id,
			kind: 'graph-node',
			label: stringValue(node.label) ?? node.id,
			value: stateLabel(node.state ?? node.status, pluginSemantics).label,
			description: stringValue(node.group)
		}))
	};
}

export function runInspection(run: RunSummary | null): RunInspection | null {
	if (!run) return null;
	return {
		runId: run.run_id,
		status: run.status,
		plugins: run.plugins.join(', ') || '-',
		pluginVersions: run.plugins.map((plugin) => `${plugin}: installed`).join(', ') || '-',
		runtimeBackend: String(
			(run as RunSummary & { runtime_backend?: string }).runtime_backend ?? 'Python'
		),
		configHash: run.config_hash,
		seedPlan: String((run as RunSummary & { seed_plan?: string }).seed_plan ?? 'manifest'),
		artifactPath: run.artifact_path ?? '-',
		startedAt: run.started_at,
		finalTime: run.final_time
	};
}

export function artifactSummaries(
	run: RunSummary | null,
	metrics: unknown[],
	events: unknown[],
	frames: SimulationFrame[]
): ArtifactSummary[] {
	if (!run) return [];
	const runBase = `/runs/${encodeURIComponent(run.run_id)}`;
	return [
		{
			kind: 'metrics',
			label: 'Metrics',
			count: metrics.length,
			href: `${runBase}/export?format=csv`
		},
		{ kind: 'events', label: 'Events', count: events.length, href: `${runBase}/export?format=csv` },
		{ kind: 'frames', label: 'Frames', count: frames.length, href: `${runBase}/frames` },
		{
			kind: 'fields',
			label: 'Field frames',
			count: frames.filter((frame) => frame.kind === 'field').length,
			href: `${runBase}/fields`
		},
		{ kind: 'manifest', label: 'Run manifest', count: 1, href: runBase }
	];
}

function fieldRows(frame: Extract<SimulationFrame, { kind: 'field' }>): BrowseFrameRow[] {
	const [, columns] = frame.shape;
	return (frame.values ?? [])
		.map((value, index) => ({
			id: `${Math.floor(index / columns)},${index % columns}`,
			kind: 'field-cell' as const,
			label: `${frame.field}[${Math.floor(index / columns)},${index % columns}]`,
			value: `${value} ${frame.units}`.trim(),
			description: null
		}))
		.sort((left, right) => Number(right.value.split(' ')[0]) - Number(left.value.split(' ')[0]))
		.slice(0, 12);
}

function groupGraphRows(
	frame: Extract<SimulationFrame, { kind: 'graph' }>,
	pluginSemantics: PluginSemantics[]
): BrowseFrameGroup[] {
	const groups = new Map<string, BrowseFrameRow[]>();
	for (const node of frame.nodes) {
		const group = stringValue(node.group);
		if (!group) return [];
		const rows = groups.get(group) ?? [];
		rows.push({
			id: node.id,
			kind: 'graph-node',
			label: stringValue(node.label) ?? node.id,
			value: stateLabel(node.state ?? node.status, pluginSemantics).label,
			description: firstMetricSummary(node, pluginSemantics)
		});
		groups.set(group, rows);
	}
	return Array.from(groups, ([id, rows]) => ({
		id,
		label: id,
		rows
	}));
}

function graphEntityType(
	frame: Extract<SimulationFrame, { kind: 'graph' }>,
	pluginSemantics: PluginSemantics[]
): string | null {
	const selectionSchema =
		(frame.visualization.selection_schema as { entity_type?: unknown } | undefined) ?? {};
	const schemaType = stringValue(selectionSchema.entity_type);
	if (schemaType) return schemaType;
	for (const plugin of pluginSemantics) {
		if (plugin.semantics.default_entity_type) return plugin.semantics.default_entity_type;
	}
	return null;
}

function entitySchemaFields(
	node: Record<string, unknown>,
	entityType: string | null,
	pluginSemantics: PluginSemantics[]
): InspectionField[] {
	if (!entityType) return fallbackFields(node);
	const schema = entityFieldsFor(entityType, pluginSemantics);
	if (!schema.length) return fallbackFields(node);
	return schema
		.map((field) => {
			const value = lookupEntityValue(node, field);
			if (value == null) return null;
			return {
				label: field.label ?? field.name,
				value: formatPrimitive(value)
			} satisfies InspectionField;
		})
		.filter((field): field is InspectionField => field !== null);
}

function nodeMetrics(node: SimulationGraphNode, pluginSemantics: PluginSemantics[]): InspectionMetric[] {
	const definitions = metricDefinitions(pluginSemantics);
	return Object.entries(node.metrics ?? {}).map(([metric, value]) => {
		const definition = definitions.get(metric);
		const formatted = typeof value === 'number' ? value.toString() : formatPrimitive(value);
		return {
			label: definition?.label ?? metric,
			value: definition?.unit ? `${formatted} ${definition.unit}` : formatted
		};
	});
}

function edgeFields(
	edge: Record<string, unknown> & { source: string; target: string }
): InspectionField[] {
	const fields: InspectionField[] = [];
	if (typeof edge.weight === 'number') {
		fields.push({ label: 'Weight', value: String(edge.weight) });
	}
	if (typeof edge.kind === 'string') {
		fields.push({ label: 'Kind', value: edge.kind });
	}
	if (typeof edge.directed === 'boolean') {
		fields.push({ label: 'Direction', value: edge.directed ? 'Directed' : 'Undirected' });
	}
	return fields;
}

function fallbackFields(node: Record<string, unknown>): InspectionField[] {
	const attrs = recordValue(node.attrs);
	const rows = Object.entries(attrs ?? {})
		.filter(([, value]) => primitiveLike(value))
		.map(([key, value]) => ({
			label: startCase(key),
			value: formatPrimitive(value)
		}));
	if (rows.length) return rows;
	return [];
}

function entityFieldsFor(entityType: string, pluginSemantics: PluginSemantics[]): EntityField[] {
	for (const plugin of pluginSemantics) {
		const fields = plugin.semantics.entity_schemas?.[entityType];
		if (fields?.length) return fields;
	}
	return [];
}

function metricDefinitions(pluginSemantics: PluginSemantics[]): Map<string, MetricDefinition> {
	const map = new Map<string, MetricDefinition>();
	for (const plugin of pluginSemantics) {
		for (const [metric, definition] of Object.entries(plugin.semantics.metric_schema ?? {})) {
			map.set(metric, definition);
		}
	}
	return map;
}

function eventDefinitions(pluginSemantics: PluginSemantics[]): Map<string, EventDefinition> {
	const map = new Map<string, EventDefinition>();
	for (const plugin of pluginSemantics) {
		for (const [eventName, definition] of Object.entries(plugin.semantics.event_schema ?? {})) {
			map.set(eventName, definition);
		}
	}
	return map;
}

function stateDefinitions(pluginSemantics: PluginSemantics[]): Map<string, StateDefinition> {
	const map = new Map<string, StateDefinition>();
	for (const plugin of pluginSemantics) {
		for (const [stateName, definition] of Object.entries(plugin.semantics.state_schema ?? {})) {
			map.set(stateName, definition);
		}
	}
	return map;
}

function stateLabel(
	value: unknown,
	pluginSemantics: PluginSemantics[]
): { label: string; description: string | null } {
	const key = typeof value === 'string' ? value : 'unknown';
	const definition = stateDefinitions(pluginSemantics).get(key);
	return {
		label: definition?.label ?? startCase(key),
		description: definition?.description ?? null
	};
}

function lookupEntityValue(node: Record<string, unknown>, field: EntityField): unknown {
	if (field.name in node) return node[field.name];
	const attrs = recordValue(node.attrs);
	if (attrs && field.name in attrs) return attrs[field.name];
	const metrics = recordValue(node.metrics);
	if (metrics && field.name in metrics) return metrics[field.name];
	return null;
}

function relatedFacts(selectionExplanation: ExplanationResponse | null): ExplanationFact[] {
	return selectionExplanation?.interpretation?.facts ?? [];
}

function eventMatchesNode(event: EventRecord, nodeId: string): boolean {
	return [event.node, event.id, event.entity, event.related_id]
		.filter(Boolean)
		.map((value) => String(value))
		.includes(nodeId);
}

function eventMatchesEdge(event: EventRecord, source: string, target: string): boolean {
	return String(event.source ?? '') === source && String(event.target ?? '') === target;
}

function labelForEventOrKind(
	value: string | null,
	definitions: Map<string, EventDefinition>
): string | null {
	if (!value) return null;
	return definitions.get(value)?.label ?? value;
}

function firstMetricSummary(
	node: SimulationGraphNode,
	pluginSemantics: PluginSemantics[]
): string | null {
	const [name, value] = Object.entries(node.metrics ?? {})[0] ?? [];
	if (!name) return null;
	const definition = metricDefinitions(pluginSemantics).get(name);
	return `${definition?.label ?? name}: ${formatPrimitive(value)}`;
}

function graphLabel(frame: Extract<SimulationFrame, { kind: 'graph' }>, nodeId: string): string {
	return stringValue(frame.nodes.find((candidate) => candidate.id === nodeId)?.label) ?? nodeId;
}

function primitiveLike(value: unknown): boolean {
	return ['string', 'number', 'boolean'].includes(typeof value);
}

function formatPrimitive(value: unknown): string {
	if (value == null) return '-';
	if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toString();
	if (typeof value === 'boolean') return value ? 'true' : 'false';
	return String(value);
}

function startCase(value: string): string {
	return value
		.replace(/[_-]+/g, ' ')
		.replace(/\b\w/g, (char) => char.toUpperCase());
}

function stringValue(value: unknown): string | null {
	return typeof value === 'string' ? value : null;
}

function numberValue(value: unknown): number | null {
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function recordValue(value: unknown): Record<string, unknown> | null {
	return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}
