import type {
	CompareResult,
	EventRecord,
	ExampleConfigResponse,
	ExampleSummary,
	ExperimentConfig,
	FieldArtifactSummary,
	FetchLike,
	FrameListResponse,
	MetricRecord,
	PluginSummary,
	RunSummary,
	SimulationFrame,
	SweepManifest,
	SweepRequest
} from './types';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8787';

export function apiBaseUrl(): string {
	return import.meta.env.PUBLIC_PERSEPHONE_API_URL ?? DEFAULT_API_BASE_URL;
}

export class PersephoneApiClient {
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

	async listFrames(
		runId: string,
		options: { kind?: 'field' | 'graph'; maxCount?: number } = {}
	): Promise<FrameListResponse> {
		const params = new URLSearchParams();
		if (options.kind) params.set('kind', options.kind);
		if (options.maxCount !== undefined) params.set('max_count', String(options.maxCount));
		const query = params.toString();
		return this.getJson(`/runs/${encodeURIComponent(runId)}/frames${query ? `?${query}` : ''}`);
	}

	async getFrame(runId: string, frameId: string): Promise<SimulationFrame> {
		return this.getJson(`/runs/${encodeURIComponent(runId)}/frames/${encodeURIComponent(frameId)}`);
	}

	async listFields(runId: string): Promise<FieldArtifactSummary[]> {
		return this.getJson(`/runs/${encodeURIComponent(runId)}/fields`);
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

	frameStreamUrl(runId: string): string {
		return this.url(`/runs/${encodeURIComponent(runId)}/frames/stream`);
	}

	exportRunUrl(runId: string, format: 'csv' | 'parquet' = 'csv'): string {
		return this.url(`/runs/${encodeURIComponent(runId)}/export?format=${format}`);
	}

	frameUrl(runId: string, frameId: string): string {
		return this.url(`/runs/${encodeURIComponent(runId)}/frames/${encodeURIComponent(frameId)}`);
	}

	fieldUrl(runId: string, fieldId: string, format: 'csv' | 'npy' = 'csv'): string {
		return this.url(
			`/runs/${encodeURIComponent(runId)}/fields/${encodeURIComponent(fieldId)}?format=${format}`
		);
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
