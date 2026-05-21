export type RunStatus = 'pending' | 'running' | 'cancelling' | 'cancelled' | 'completed' | 'failed';

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
};

export type PluginSummary = {
	name: string;
	version: string;
	paradigm: string;
	trust_level?: string;
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
			nodes: Array<Record<string, unknown> & { id: string }>;
			edges: Array<Record<string, unknown> & { source: string; target: string }>;
			visualization: Record<string, unknown>;
	  } & Omit<FrameListEntry, 'payload_ref'>);

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;
