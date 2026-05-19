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

export type ExperimentConfig = {
	name: string;
	description?: string;
	seed: number;
	scheduler: {
		t_end: number;
		sync_interval: 'auto' | number;
	};
	solvers: Array<{
		type: 'graph';
		plugin: 'sir_epidemic';
		version: string;
		params: {
			contact_graph: string;
			n_nodes: number;
			initially_infected: number[];
			p_infect: number;
			p_recover: number;
		};
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
};

export const sirExampleJsonSchema = {
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

export type SirEditorValues = {
	seed: number;
	tEnd: number;
	pInfect: number;
	pRecover: number;
	initiallyInfected: number[];
};

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

	async getSirExampleConfig(): Promise<ExperimentConfig> {
		return this.getJson('/examples/sir_epidemic');
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

export function parseInitialInfected(value: string): number[] {
	const nodes = value
		.split(',')
		.map((item) => Number.parseInt(item.trim(), 10))
		.filter((item) => Number.isFinite(item));
	return [...new Set(nodes)];
}

export function validateSirValues(values: SirEditorValues): string[] {
	const errors: string[] = [];
	if (!Number.isInteger(values.seed)) errors.push('Seed must be an integer.');
	if (values.tEnd <= 0) errors.push('Simulation duration must be positive.');
	if (values.pInfect < 0 || values.pInfect > 1) {
		errors.push('Infection probability must be between 0 and 1.');
	}
	if (values.pRecover < 0 || values.pRecover > 1) {
		errors.push('Recovery probability must be between 0 and 1.');
	}
	if (values.initiallyInfected.length === 0) {
		errors.push('At least one initially infected node is required.');
	}
	if (values.initiallyInfected.some((node) => node < 0 || node > 19)) {
		errors.push('Initially infected nodes must be between 0 and 19.');
	}
	return errors;
}

export function validateExperimentConfigAgainstSchema(config: ExperimentConfig): string[] {
	const errors: string[] = [];
	if (!config.name) errors.push('Experiment name is required.');
	if (!Number.isInteger(config.seed)) errors.push('Config seed must be an integer.');
	if (config.scheduler.t_end <= 0) errors.push('Config duration must be positive.');
	if (config.solvers.length === 0) errors.push('At least one solver is required.');
	if (config.solvers[0]?.plugin !== 'sir_epidemic') {
		errors.push('The bundled editor expects the sir_epidemic plugin.');
	}
	return errors;
}

export function buildSirExampleConfig(values: SirEditorValues): ExperimentConfig {
	return {
		name: 'sir_epidemic_baseline',
		description: 'Synthetic 20-node SIR contact-network simulation',
		seed: values.seed,
		scheduler: {
			t_end: values.tEnd,
			sync_interval: 'auto'
		},
		solvers: [
			{
				type: 'graph',
				plugin: 'sir_epidemic',
				version: '>=0.1.0',
				params: {
					contact_graph: 'configs/examples/data/sir_contact_edges.csv',
					n_nodes: 20,
					initially_infected: values.initiallyInfected,
					p_infect: values.pInfect,
					p_recover: values.pRecover
				}
			}
		],
		observer: {
			metrics: [
				'susceptible_count',
				'infected_count',
				'recovered_count',
				'new_infections',
				'new_recoveries',
				'r_effective_estimate'
			],
			emit_every: 1
		},
		storage: {
			artifacts_dir: 'runs',
			metrics: true,
			events: true
		}
	};
}

export function metricSeries(records: MetricRecord[]): Record<string, MetricRecord[]> {
	return records.reduce<Record<string, MetricRecord[]>>((series, record) => {
		series[record.metric] ??= [];
		series[record.metric].push(record);
		return series;
	}, {});
}
