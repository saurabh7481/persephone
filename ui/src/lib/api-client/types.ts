export type RunStatus = 'pending' | 'running' | 'cancelling' | 'cancelled' | 'completed' | 'failed';
export type InterpretationMode = 'off' | 'rules_only' | 'minimal_ai';
export type ExplanationSeverity = 'info' | 'notice' | 'warning' | 'critical';

export type RunSummary = {
	run_id: string;
	name: string;
	status: RunStatus;
	started_at: string;
	final_time: number;
	plugins: string[];
	config_hash: string;
	artifact_path: string | null;
	error_message: string | null;
	cancel_requested?: boolean;
	plugin_semantics?: PluginSemantics[];
};

export type PluginSummary = {
	name: string;
	version: string;
	paradigm: string;
	trust_level?: string;
};

export type EntityField = {
	name: string;
	type: 'string' | 'integer' | 'number' | 'boolean' | 'categorical' | 'enum' | 'json';
	label?: string | null;
	description?: string | null;
	unit?: string | null;
	required?: boolean;
};

export type StateDefinition = {
	name: string;
	kind: 'categorical' | 'continuous' | 'ordinal' | 'boolean';
	label?: string | null;
	description?: string | null;
	unit?: string | null;
	values?: string[];
};

export type MetricDefinition = {
	name: string;
	label?: string | null;
	kind?: 'scalar' | 'ratio' | 'delta' | 'index';
	description?: string | null;
	unit?: string | null;
	headline?: boolean;
};

export type EventDefinition = {
	name: string;
	label?: string | null;
	description?: string | null;
	related_entity?: string | null;
};

export type ViewCapability = {
	kind:
		| 'network'
		| 'positioned_graph'
		| 'map_network'
		| 'matrix'
		| 'table'
		| 'timeline'
		| 'heatmap'
		| 'hierarchy';
	label?: string | null;
	description?: string | null;
	default?: boolean;
	requires_coordinates?: boolean;
};

export type ExplanationCapability = {
	scope: 'run' | 'frame' | 'selection';
	label?: string | null;
	description?: string | null;
	fact_kinds?: string[];
};

export type SemanticManifest = {
	entity_schemas?: Record<string, EntityField[]>;
	state_schema?: Record<string, StateDefinition>;
	metric_schema?: Record<string, MetricDefinition>;
	event_schema?: Record<string, EventDefinition>;
	view_capabilities?: ViewCapability[];
	explanation_capabilities?: ExplanationCapability[];
	default_entity_type?: string | null;
	preferred_view?: string | null;
};

export type PluginSemantics = {
	name: string;
	version: string;
	semantics: SemanticManifest;
};

export type FactEvidence = {
	label: string;
	value?: string | number | boolean | null;
	metric?: string | null;
	unit?: string | null;
	source?: string | null;
};

export type ExplanationFact = {
	kind: 'trend' | 'milestone' | 'anomaly' | 'hotspot' | 'selection';
	title: string;
	summary: string;
	severity: ExplanationSeverity;
	evidence?: FactEvidence[];
	related_ids?: string[];
	t: number;
};

export type ExplanationSummary = {
	title: string;
	summary: string;
	severity: ExplanationSeverity;
	evidence?: FactEvidence[];
	fact_count: number;
};

export type InterpretationResult = {
	run_id: string;
	scope: 'run' | 'frame' | 'selection';
	t: number;
	tick: number;
	frame_id?: string | null;
	selection_id?: string | null;
	mode_requested: InterpretationMode;
	mode_applied: InterpretationMode;
	label: string;
	cached: boolean;
	facts: ExplanationFact[];
	summary?: ExplanationSummary | null;
};

export type ExplanationResponse = {
	run_id: string;
	scope: 'run' | 'frame' | 'selection';
	frame_id?: string | null;
	selection_id?: string | null;
	available: boolean;
	reason?: string | null;
	interpretation?: InterpretationResult | null;
};

export type FieldArtifactSummary = {
	field_id?: string;
	id?: string;
	name?: string;
	path?: string;
	shape?: number[];
	dtype?: string;
	units?: string;
	[key: string]: unknown;
};

export type MetricRecord = {
	t: number;
	metric: string;
	value: number;
	[key: string]: unknown;
};

export type EventRecord = {
	t?: number;
	event?: string;
	event_type?: string;
	type?: string;
	[key: string]: unknown;
};

export type SweepValue = boolean | number | string;

export type SweepRequest = {
	sweep_id?: string | null;
	name: string;
	base_config: ExperimentConfig;
	parameter: string;
	values: SweepValue[];
};

export type SweepChildRun = {
	run_id: string;
	value: SweepValue;
	status: RunStatus;
	artifact_path: string;
};

export type SweepManifest = {
	sweep_id: string;
	name: string;
	parameter: string;
	values: SweepValue[];
	created_at?: string;
	child_runs: SweepChildRun[];
};

export type CompareAlignedRow = {
	t: number;
	run_a: number | null;
	run_b: number | null;
};

export type CompareMetricSummary = {
	peak: number;
	final: number;
	auc: number;
};

export type CompareResult = {
	run_a: string;
	run_b: string;
	metric: string;
	aligned: CompareAlignedRow[];
	summaries: Record<string, CompareMetricSummary>;
};

export type ExperimentConfig = {
	name: string;
	description?: string;
	seed: number;
	scheduler: {
		t_end: number;
		sync_interval: 'auto' | number;
		demo_delay_ms_per_tick?: number;
	};
	solvers: Array<{
		type: string;
		plugin: string;
		version: string;
		params: Record<string, unknown>;
	}>;
	observer: {
		metrics: string[];
		emit_every: number;
	};
	storage: {
		artifacts_dir: string;
		metrics: boolean;
		events: boolean;
	};
	visualization?: {
		emit_every: number;
		inline_frame_max_values?: number;
	};
	interpretation?: {
		mode?: InterpretationMode;
		every_n_ticks?: number;
		on_milestone?: boolean;
		on_complete?: boolean;
		max_input_facts?: number;
		max_output_tokens?: number;
		store_records?: boolean;
	};
};

export type ExampleSummary = {
	id: string;
	name: string;
	description: string;
};

export type ExampleConfigResponse = ExampleSummary & {
	config: ExperimentConfig;
};

export type FramePayloadRef = {
	uri: string;
	format: 'json' | 'jsonl' | 'npz' | 'npy' | 'zarr' | 'parquet';
	byte_offset?: number | null;
	byte_length?: number | null;
};

export type FrameListEntry = {
	frame_id: string;
	kind: 'field' | 'graph';
	t: number;
	tick: number;
	solver_id: string;
	source: string;
	payload_ref: FramePayloadRef;
};

export type FrameListResponse = {
	metadata: {
		run_id: string;
		frame_count: number;
		available_kinds: string[];
		t_min: number | null;
		t_max: number | null;
	};
	frames: FrameListEntry[];
};

export type SimulationFrame =
	| ({
			kind: 'field';
			field: string;
			shape: [number, number];
			dtype: string;
			bounds: Record<string, number>;
			units: string;
			visualization: Record<string, unknown>;
			values?: number[] | null;
			payload_ref?: FramePayloadRef | null;
	  } & Omit<FrameListEntry, 'payload_ref'>)
	| ({
			kind: 'graph';
			nodes: Array<
				Record<string, unknown> & {
					id: string;
					x?: number | null;
					y?: number | null;
					state?: string | null;
					label?: string | null;
					group?: string | null;
					lat?: number | null;
					lon?: number | null;
					metrics?: Record<string, number> | null;
					attrs?: Record<string, unknown> | null;
				}
			>;
			edges: Array<
				Record<string, unknown> & {
					source: string;
					target: string;
					weight?: number | null;
					kind?: string | null;
					directed?: boolean | null;
					attrs?: Record<string, unknown> | null;
				}
			>;
			visualization: Record<string, unknown> & {
				layout_hint?: string | null;
				coordinate_system?: string | null;
				preferred_view?: string | null;
				legend?: Record<string, unknown> | null;
				selection_schema?: Record<string, unknown> | null;
				density_hint?: string | null;
			};
	  } & Omit<FrameListEntry, 'payload_ref'>);

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;
