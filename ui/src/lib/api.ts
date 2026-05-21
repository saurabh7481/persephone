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

export const experimentConfigJsonSchema = {
	type: 'object',
	required: ['name', 'seed', 'scheduler', 'solvers', 'observer', 'storage'],
	properties: {
		name: { type: 'string', minLength: 1 },
		seed: { type: 'integer' },
		scheduler: {
			type: 'object',
			required: ['t_end', 'sync_interval'],
			properties: {
				t_end: { type: 'number', exclusiveMinimum: 0 },
				sync_interval: { oneOf: [{ const: 'auto' }, { type: 'number', exclusiveMinimum: 0 }] }
			}
		},
		solvers: {
			type: 'array',
			minItems: 1
		}
	}
} as const;

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8787';

export function apiBaseUrl(): string {
	return import.meta.env.PUBLIC_PERSEPHONE_API_URL ?? DEFAULT_API_BASE_URL;
}

export class PersephoneApi {
	constructor(
		private readonly baseUrl = apiBaseUrl(),
		private readonly fetcher: FetchLike = fetch
	) {}

	async listRuns(): Promise<RunSummary[]> {
		return this.getJson('/runs');
	}

	async getRun(runId: string): Promise<RunSummary> {
		return this.getJson(`/runs/${encodeURIComponent(runId)}`);
	}

	async getMetrics(runId: string): Promise<MetricRecord[]> {
		return this.getJson(`/runs/${encodeURIComponent(runId)}/metrics`);
	}

	async getEvents(runId: string): Promise<EventRecord[]> {
		return this.getJson(`/runs/${encodeURIComponent(runId)}/events`);
	}

	async listPlugins(): Promise<PluginSummary[]> {
		return this.getJson('/plugins');
	}

	async listExamples(): Promise<ExampleSummary[]> {
		return this.getJson('/examples');
	}

	async getExampleConfig(exampleId: string): Promise<ExampleConfigResponse> {
		return this.getJson(`/examples/${encodeURIComponent(exampleId)}`);
	}

	async startRun(config: ExperimentConfig): Promise<RunSummary> {
		const response = await this.fetcher(this.url('/runs'), {
			method: 'POST',
			headers: {
				accept: 'application/json',
				'content-type': 'application/json'
			},
			body: JSON.stringify({ config })
		});
		return parseJsonResponse<RunSummary>(response);
	}

	async startSweep(request: SweepRequest): Promise<SweepManifest> {
		const response = await this.fetcher(this.url('/sweeps'), {
			method: 'POST',
			headers: {
				accept: 'application/json',
				'content-type': 'application/json'
			},
			body: JSON.stringify(request)
		});
		return parseJsonResponse<SweepManifest>(response);
	}

	async compareRuns(runA: string, runB: string, metric: string): Promise<CompareResult> {
		const params = new URLSearchParams();
		params.append('run', runA);
		params.append('run', runB);
		params.set('metric', metric);
		return this.getJson(`/compare?${params.toString()}`);
	}

	streamUrl(runId: string): string {
		return this.url(`/runs/${encodeURIComponent(runId)}/stream`);
	}

	private async getJson<T>(path: string): Promise<T> {
		const response = await this.fetcher(this.url(path), {
			headers: { accept: 'application/json' }
		});
		return parseJsonResponse<T>(response);
	}

	private url(path: string): string {
		return `${this.baseUrl.replace(/\/$/, '')}${path}`;
	}
}

export async function parseJsonResponse<T>(response: Response): Promise<T> {
	if (!response.ok) {
		throw new Error(`API request failed with ${response.status}`);
	}
	return (await response.json()) as T;
}

export function validateExperimentConfigAgainstSchema(config: ExperimentConfig): string[] {
	const errors: string[] = [];
	if (!config.name) errors.push('Experiment name is required.');
	if (!Number.isInteger(config.seed)) errors.push('Config seed must be an integer.');
	if (config.scheduler.t_end <= 0) errors.push('Config duration must be positive.');
	if (config.solvers.length === 0) errors.push('At least one solver is required.');
	return errors;
}

export function metricSeries(records: MetricRecord[]): Record<string, MetricRecord[]> {
	return records.reduce<Record<string, MetricRecord[]>>((series, record) => {
		series[record.metric] ??= [];
		series[record.metric].push(record);
		return series;
	}, {});
}

export function compareMetricSummary(records: MetricRecord[]): {
	peakValue: number;
	finalValue: number;
	primaryMetric: string;
	duration: number;
} {
	const primaryMetric = firstDomainMetric(records);
	const primaryRecords = records.filter((record) => record.metric === primaryMetric);
	return {
		peakValue: Math.max(0, ...primaryRecords.map((record) => record.value)),
		finalValue: primaryRecords.at(-1)?.value ?? 0,
		primaryMetric,
		duration: Math.max(0, ...records.map((record) => record.t))
	};
}

export function firstDomainMetric(records: MetricRecord[]): string {
	return records.find((record) => !record.metric.startsWith('scheduler.'))?.metric ?? 'metric';
}

export function sweepValuesFromText(value: string): SweepValue[] {
	return value
		.split(',')
		.map((item) => item.trim())
		.filter(Boolean)
		.map((item) => {
			if (item === 'true') return true;
			if (item === 'false') return false;
			const numeric = Number(item);
			return Number.isFinite(numeric) ? numeric : item;
		});
}
