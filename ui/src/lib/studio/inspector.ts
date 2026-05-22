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
import {
	formatMetricValue,
	formatNumber,
	formatTimeLabel,
	formatUnknownValue,
	humanizeIdentifier
} from '$lib/studio/format';

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
	summary: string | null;
	facts: ExplanationFact[];
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
	summary: string | null;
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
	summary: string | null;
	events: EventRecord[];
	facts: ExplanationFact[];
	fields: InspectionField[];
	edge: Record<string, unknown> & { source: string; target: string };
};

export type InspectorPanelItem = {
	label: string;
	value: string;
	description?: string;
};

export type InspectorPanelSection = {
	title: string;
	description?: string;
	items: InspectorPanelItem[];
};

export type InspectorPanelModel = {
	kind: 'empty' | 'field-cell' | 'graph-node' | 'graph-edge';
	eyebrow: string;
	title: string;
	summary: string;
	highlights: InspectorPanelItem[];
	sections: InspectorPanelSection[];
	technical: InspectorPanelItem[];
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
	cellId: string | null,
	selectionExplanation: ExplanationResponse | null = null
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
		source: frame.source,
		summary: selectionExplanation?.interpretation?.summary?.summary ?? null,
		facts: relatedFacts(selectionExplanation, cellId)
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
		summary: selectionExplanation?.interpretation?.summary?.summary ?? null,
		metrics: nodeMetrics(node, pluginSemantics),
		fields: entitySchemaFields(node, entityType, pluginSemantics),
		events: events.filter((event) => eventMatchesNode(event, nodeId)),
		facts: relatedFacts(selectionExplanation, nodeId),
		node,
		...(eventSchema.size ? {} : {})
	};
}

export function graphEdgeInspection(
	frame: SimulationFrame | null,
	edgeId: string | null,
	events: EventRecord[],
	pluginSemantics: PluginSemantics[] = [],
	selectionExplanation: ExplanationResponse | null = null
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
		summary: selectionExplanation?.interpretation?.summary?.summary ?? null,
		events: events.filter((event) => eventMatchesEdge(event, edge.source, edge.target)),
		facts: relatedFacts(selectionExplanation, edgeId),
		fields: edgeFields(edge),
		edge
	};
}

export function buildInspectorPanelModel({
	selectedFrame,
	fieldCell,
	graphNode,
	graphEdge,
	run
}: {
	selectedFrame: SimulationFrame | null;
	fieldCell: FieldCellInspection | null;
	graphNode: GraphNodeInspection | null;
	graphEdge: GraphEdgeInspection | null;
	run: RunInspection | null;
}): InspectorPanelModel {
	if (graphNode) return graphNodePanel(graphNode, selectedFrame, run);
	if (graphEdge) return graphEdgePanel(graphEdge, selectedFrame, run);
	if (fieldCell) return fieldCellPanel(fieldCell, selectedFrame, run);
	return emptyPanel(selectedFrame, run);
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
				value: edge.kind
					? String(edge.kind)
					: edge.weight == null
						? 'relationship'
						: `${edge.weight}`,
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

export type InspectorPreview = {
	title: string;
	summary: string;
	hasMeaningfulSelection: boolean;
};

export function inspectorPreview(model: InspectorPanelModel): InspectorPreview {
	if (model.kind === 'empty') {
		return {
			title: 'Inspector ready',
			summary: 'Select a node, relationship, or field cell to inspect why it matters.',
			hasMeaningfulSelection: false
		};
	}
	return {
		title: model.title,
		summary: model.summary,
		hasMeaningfulSelection: true
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

function nodeMetrics(
	node: SimulationGraphNode,
	pluginSemantics: PluginSemantics[]
): InspectionMetric[] {
	const definitions = metricDefinitions(pluginSemantics);
	return Object.entries(node.metrics ?? {}).map(([metric, value]) => {
		const definition = definitions.get(metric);
		return {
			label: definition?.label ?? humanizeIdentifier(metric),
			value:
				typeof value === 'number'
					? formatMetricValue(value, definition?.unit ?? null)
					: formatUnknownValue(value, definition?.unit ?? null)
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
			label: humanizeIdentifier(key),
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

function relatedFacts(
	selectionExplanation: ExplanationResponse | null,
	relatedId: string
): ExplanationFact[] {
	return (selectionExplanation?.interpretation?.facts ?? []).filter((fact) => {
		const relatedIds = fact.related_ids ?? [];
		return relatedIds.length === 0 || relatedIds.includes(relatedId);
	});
}

function graphNodePanel(
	node: GraphNodeInspection,
	selectedFrame: SimulationFrame | null,
	run: RunInspection | null
): InspectorPanelModel {
	const whyItMatters =
		node.facts[0]?.summary ??
		node.stateDescription ??
		(node.metrics[0] ? `${node.metrics[0].label} is the strongest local signal right now.` : '');
	const sections = [
		buildSection('Current state', [
			{ label: 'State', value: node.state },
			...(node.entityType
				? [{ label: 'Entity type', value: humanizeIdentifier(node.entityType) }]
				: []),
			...(node.group ? [{ label: 'Group', value: humanizeIdentifier(node.group) }] : [])
		]),
		buildSection('Local metrics', node.metrics.map(panelItemFromField)),
		buildSection('Attributes', node.fields.map(panelItemFromField)),
		buildSection('Recent related events', node.events.slice(0, 3).map(panelItemFromEvent)),
		buildSection('Linked explanation facts', node.facts.map(panelItemFromFact))
	].filter((section): section is InspectorPanelSection => section !== null);

	return {
		kind: 'graph-node',
		eyebrow: 'Entity inspector',
		title: node.label,
		summary:
			node.summary ??
			whyItMatters ??
			`${node.label} is currently ${node.state.toLowerCase()} in the selected frame.`,
		highlights: [
			{ label: 'Current state', value: node.state },
			...(whyItMatters ? [{ label: 'Why it matters', value: whyItMatters }] : [])
		],
		sections,
		technical: compactItems([
			{ label: 'Node id', value: node.id },
			{ label: 'Degree', value: formatNumber(node.degree, { maximumFractionDigits: 0 }) },
			{ label: 'Frame', value: selectedFrame?.frame_id ?? '-' },
			{ label: 'Run', value: run?.runId ?? '-' }
		])
	};
}

function graphEdgePanel(
	edge: GraphEdgeInspection,
	selectedFrame: SimulationFrame | null,
	run: RunInspection | null
): InspectorPanelModel {
	const relationshipSummary = edge.facts[0]?.summary ?? relationshipLead(edge);
	const sections = [
		buildSection('Current relationship', [
			{ label: 'Kind', value: humanizeIdentifier(edge.kind) },
			{ label: 'Direction', value: edge.directed ? 'Directed' : 'Undirected' },
			...(edge.weight == null ? [] : [{ label: 'Weight', value: formatNumber(edge.weight) }])
		]),
		buildSection('Attributes', edge.fields.map(panelItemFromField)),
		buildSection('Recent related events', edge.events.slice(0, 3).map(panelItemFromEvent)),
		buildSection('Linked explanation facts', edge.facts.map(panelItemFromFact))
	].filter((section): section is InspectorPanelSection => section !== null);

	return {
		kind: 'graph-edge',
		eyebrow: 'Entity inspector',
		title: edge.label,
		summary: edge.summary ?? relationshipSummary,
		highlights: [
			{ label: 'Relationship', value: humanizeIdentifier(edge.kind) },
			{ label: 'Why it matters', value: relationshipSummary }
		],
		sections,
		technical: compactItems([
			{ label: 'Relationship id', value: edge.id },
			{ label: 'Frame', value: selectedFrame?.frame_id ?? '-' },
			{ label: 'Run', value: run?.runId ?? '-' }
		])
	};
}

function fieldCellPanel(
	cell: FieldCellInspection,
	selectedFrame: SimulationFrame | null,
	run: RunInspection | null
): InspectorPanelModel {
	const reading = formatUnknownValue(cell.value, cell.units);
	const whyItMatters =
		cell.facts[0]?.summary ?? `${cell.label} is the active reading in the selected field frame.`;
	const sections = [
		buildSection('Current reading', [
			{ label: 'Value', value: reading },
			{ label: 'Field', value: humanizeIdentifier(cell.field) },
			{ label: 'Coordinates', value: `${cell.row}, ${cell.column}` }
		]),
		buildSection('Linked explanation facts', cell.facts.map(panelItemFromFact))
	].filter((section): section is InspectorPanelSection => section !== null);

	return {
		kind: 'field-cell',
		eyebrow: 'Entity inspector',
		title: cell.label,
		summary: cell.summary ?? whyItMatters,
		highlights: [
			{ label: 'Current value', value: reading },
			{ label: 'Why it matters', value: whyItMatters }
		],
		sections,
		technical: compactItems([
			{ label: 'Field type', value: cell.dtype },
			{ label: 'Shape', value: cell.shape.join('x') },
			{ label: 'Source', value: cell.source },
			{ label: 'Frame', value: selectedFrame?.frame_id ?? cell.frameId },
			{ label: 'Run', value: run?.runId ?? '-' }
		])
	};
}

function emptyPanel(
	selectedFrame: SimulationFrame | null,
	run: RunInspection | null
): InspectorPanelModel {
	return {
		kind: 'empty',
		eyebrow: 'Entity inspector',
		title: 'Select a node, relationship, or field cell',
		summary:
			'The inspector will explain why the selected entity matters once you click something in the active view.',
		highlights: compactItems([
			{ label: 'Selected frame', value: selectedFrame?.frame_id ?? 'none' },
			{ label: 'Frame kind', value: selectedFrame?.kind ?? '-' }
		]),
		sections: [],
		technical: compactItems([
			{ label: 'Run', value: run?.runId ?? '-' },
			{ label: 'Status', value: run?.status ?? '-' }
		])
	};
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
	return `${definition?.label ?? humanizeIdentifier(name)}: ${formatPrimitive(value)}`;
}

function graphLabel(frame: Extract<SimulationFrame, { kind: 'graph' }>, nodeId: string): string {
	return stringValue(frame.nodes.find((candidate) => candidate.id === nodeId)?.label) ?? nodeId;
}

function primitiveLike(value: unknown): boolean {
	return ['string', 'number', 'boolean'].includes(typeof value);
}

function formatPrimitive(value: unknown): string {
	if (value == null) return '-';
	if (typeof value === 'number') {
		return Number.isInteger(value)
			? formatNumber(value, { maximumFractionDigits: 0 })
			: formatNumber(value);
	}
	if (typeof value === 'boolean') return value ? 'Yes' : 'No';
	return String(value);
}

function startCase(value: string): string {
	return value.replace(/[_-]+/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
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

function buildSection(title: string, items: InspectorPanelItem[]): InspectorPanelSection | null {
	const compact = compactItems(items);
	if (!compact.length) return null;
	return { title, items: compact };
}

function panelItemFromField(field: InspectionField): InspectorPanelItem {
	return { label: field.label, value: field.value };
}

function panelItemFromEvent(event: EventRecord): InspectorPanelItem {
	return {
		label: eventLabel(event),
		value: formatTimeLabel(typeof event.t === 'number' ? event.t : null),
		description: eventContext(event)
	};
}

function panelItemFromFact(fact: ExplanationFact): InspectorPanelItem {
	return {
		label: fact.title,
		value: formatTimeLabel(fact.t),
		description: fact.summary
	};
}

function compactItems(items: InspectorPanelItem[]): InspectorPanelItem[] {
	return items.filter((item) => item.value && item.value !== '-');
}

function eventLabel(event: EventRecord): string {
	const base = humanizeIdentifier(String(event.event_type ?? event.event ?? event.type ?? 'event'));
	return /event$/i.test(base) ? base : `${base} event`;
}

function eventContext(event: EventRecord): string | undefined {
	if (event.node != null) return `Related entity ${String(event.node)}`;
	if (event.source != null && event.target != null) {
		return `${String(event.source)} -> ${String(event.target)}`;
	}
	return undefined;
}

function relationshipLead(edge: GraphEdgeInspection): string {
	const direction = edge.directed ? 'directed' : 'undirected';
	if (edge.weight == null) {
		return `${edge.label} is a ${direction} ${humanizeIdentifier(edge.kind)} relationship in the current frame.`;
	}
	return `${edge.label} is a ${direction} ${humanizeIdentifier(edge.kind)} relationship with weight ${formatNumber(edge.weight)}.`;
}
