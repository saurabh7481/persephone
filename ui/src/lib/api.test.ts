import { describe, expect, test, vi } from 'vitest';

import {
	PersephoneApi,
	compareMetricSummary,
	experimentConfigJsonSchema,
	metricSeries,
	sweepValuesFromText,
	validateExperimentConfigAgainstSchema,
	type ExperimentConfig
} from './api';

function demoConfig(): ExperimentConfig {
	return {
		name: 'demo',
		seed: 1,
		scheduler: { t_end: 2, sync_interval: 'auto' },
		solvers: [{ type: 'graph', plugin: 'demo_plugin', version: '>=0.1.0', params: {} }],
		observer: { metrics: ['metric_a'], emit_every: 1 },
		storage: { artifacts_dir: 'runs', metrics: true, events: true }
	};
}

describe('PersephoneApi', () => {
	test('lists runs from the configured API base URL', async () => {
		const fetcher = vi.fn(async () => {
			return new Response(
				JSON.stringify([
					{
						run_id: 'run-a',
						name: 'baseline',
						status: 'completed',
						started_at: '2026-05-19T00:00:00Z',
						final_time: 24,
						plugins: ['demo_plugin'],
						config_hash: 'abc',
						artifact_path: 'runs/run-a',
						error_message: null
					}
				])
			);
		});

		const api = new PersephoneApi('http://api.local', fetcher);
		const runs = await api.listRuns();

		expect(fetcher).toHaveBeenCalledWith('http://api.local/runs', {
			headers: { accept: 'application/json' }
		});
		expect(runs[0]?.run_id).toBe('run-a');
	});

	test('validates generic experiment configs', () => {
		const config = demoConfig();

		expect(config.seed).toBe(1);
		expect(config.scheduler.t_end).toBe(2);
		expect(config.solvers[0]?.plugin).toBe('demo_plugin');
		expect(validateExperimentConfigAgainstSchema(config)).toEqual([]);
		expect(experimentConfigJsonSchema.properties.seed.type).toBe('integer');
	});

	test('groups metrics into chart series', () => {
		const series = metricSeries([
			{ t: 1, metric: 'metric_a', value: 3 },
			{ t: 2, metric: 'metric_a', value: 5 },
			{ t: 1, metric: 'metric_b', value: 0 }
		]);

		expect(series.metric_a?.map((point) => point.value)).toEqual([3, 5]);
		expect(series.metric_b?.[0]?.t).toBe(1);
	});

	test('posts sweep requests and builds stream URLs', async () => {
		const fetcher = vi.fn(async () => {
			return new Response(
				JSON.stringify({
					sweep_id: 'ui-sweep',
					name: 'UI sweep',
					parameter: 'solvers[0].params.rate',
					values: [0.2, 0.4],
					child_runs: []
				}),
				{ status: 201 }
			);
		});
		const api = new PersephoneApi('http://api.local/', fetcher);

		const sweep = await api.startSweep({
			sweep_id: 'ui-sweep',
			name: 'UI sweep',
			base_config: demoConfig(),
			parameter: 'solvers[0].params.rate',
			values: [0.2, 0.4]
		});

		expect(fetcher).toHaveBeenCalledWith('http://api.local/sweeps', expect.any(Object));
		expect(api.streamUrl('run-a')).toBe('http://api.local/runs/run-a/stream');
		expect(sweep.sweep_id).toBe('ui-sweep');
	});

	test('parses sweep values and computes compact metric summaries', () => {
		expect(sweepValuesFromText('0.2, 0.4, label')).toEqual([0.2, 0.4, 'label']);
		expect(
			compareMetricSummary([
				{ t: 1, metric: 'metric_a', value: 3 },
				{ t: 2, metric: 'metric_a', value: 5 },
				{ t: 2, metric: 'metric_b', value: 10 }
			])
		).toEqual({ peakValue: 5, finalValue: 5, primaryMetric: 'metric_a', duration: 2 });
	});
});
