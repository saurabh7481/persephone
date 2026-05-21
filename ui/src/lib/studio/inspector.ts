import type { EventRecord, MetricRecord, RunSummary, SimulationFrame } from '$lib/api-client';

export type FieldCellInspection = {
	id: string;
	row: number;
	column: number;
	value: number | null;
	units: string;
	field: string;
	dtype: string;
	shape: [number, number];
	frameId: string;
	source: string;
};

export type GraphNodeInspection = {
	id: string;
	state: string;
	degree: number;
	events: EventRecord[];
	node: Record<string, unknown> & { id: string };
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
		dtype: frame.dtype,
		shape: frame.shape,
		frameId: frame.frame_id,
		source: frame.source
	};
}

export function graphNodeInspection(
	frame: SimulationFrame | null,
	nodeId: string | null,
	events: EventRecord[]
): GraphNodeInspection | null {
	if (!frame || frame.kind !== 'graph' || !nodeId) return null;
	const node = frame.nodes.find((candidate) => candidate.id === nodeId);
	if (!node) return null;
	const degree = frame.edges.filter(
		(edge) => edge.source === nodeId || edge.target === nodeId
	).length;
	return {
		id: node.id,
		state: String(node.state ?? node.status ?? 'unknown'),
		degree,
		events: events.filter((event) => String(event.node ?? event.id ?? '') === nodeId),
		node
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
	metrics: MetricRecord[],
	events: EventRecord[],
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
