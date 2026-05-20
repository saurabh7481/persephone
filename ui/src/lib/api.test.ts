import { describe, expect, test, vi } from 'vitest';

import {
	PersephoneApi,
	buildSirExampleConfig,
	compareMetricSummary,
	metricSeries,
	parseInitialInfected,
	sirExampleJsonSchema,
	sweepValuesFromText,
	validateExperimentConfigAgainstSchema
} from './api';

describe('PersephoneApi', () => {
	test('lists runs from the configured API base URL', async () => {
		const fetcher = vi.fn(async () => {
			return new Response(
				JSON.stringify([
					{
						run_id: 'run-a',
						name: 'SIR baseline',
						status: 'completed',
						started_at: '2026-05-19T00:00:00Z',
						final_time: 24,
						plugins: ['sir_epidemic'],
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

	test('builds a SIR example config from editor values', () => {
		const config = buildSirExampleConfig({
			seed: 99,
			tEnd: 12,
			pInfect: 0.4,
			pRecover: 0.2,
			initiallyInfected: [0, 5]
		});

		expect(config.seed).toBe(99);
		expect(config.scheduler.t_end).toBe(12);
		expect(config.solvers[0]?.params.p_infect).toBe(0.4);
		expect(config.solvers[0]?.params.initially_infected).toEqual([0, 5]);
		expect(validateExperimentConfigAgainstSchema(config)).toEqual([]);
		expect(sirExampleJsonSchema.properties.seed.type).toBe('integer');
	});

	test('parses comma separated initially infected nodes', () => {
		expect(parseInitialInfected('0, 10, 17')).toEqual([0, 10, 17]);
	});

	test('groups metrics into chart series', () => {
		const series = metricSeries([
			{ t: 1, metric: 'infected_count', value: 3 },
			{ t: 2, metric: 'infected_count', value: 5 },
			{ t: 1, metric: 'recovered_count', value: 0 }
		]);

		expect(series.infected_count?.map((point) => point.value)).toEqual([3, 5]);
		expect(series.recovered_count?.[0]?.t).toBe(1);
	});

	test('posts sweep requests and builds stream URLs', async () => {
		const fetcher = vi.fn(async () => {
			return new Response(
				JSON.stringify({
					sweep_id: 'ui-sweep',
					name: 'UI sweep',
					parameter: 'solvers[0].params.p_infect',
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
			base_config: buildSirExampleConfig({
				seed: 1,
				tEnd: 2,
				pInfect: 0.2,
				pRecover: 0.1,
				initiallyInfected: [0]
			}),
			parameter: 'solvers[0].params.p_infect',
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
				{ t: 1, metric: 'infected_count', value: 3 },
				{ t: 2, metric: 'infected_count', value: 5 },
				{ t: 2, metric: 'recovered_count', value: 10 }
			])
		).toEqual({ peakInfected: 5, finalRecovered: 10, duration: 2 });
	});
});
