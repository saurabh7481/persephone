import { describe, expect, test, vi } from 'vitest';

import {
	PersephoneApi,
	buildSirExampleConfig,
	metricSeries,
	parseInitialInfected,
	sirExampleJsonSchema,
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
});
