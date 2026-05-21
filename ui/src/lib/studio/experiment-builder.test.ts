import { describe, expect, test } from 'vitest';

import {
	assignConfigPath,
	friendlyLabel,
	scalarParameterPaths,
	validateBuilderConfig
} from './experiment-builder';
import type { ExperimentConfig } from '$lib/api-client';

const config: ExperimentConfig = {
	name: 'baseline',
	seed: 42,
	scheduler: { t_end: 24, sync_interval: 'auto' },
	solvers: [
		{
			type: 'graph',
			plugin: 'demo_plugin',
			version: '>=0.1.0',
			params: {
				rate_a: 0.6,
				rate_b: 0.08,
				initial_nodes: [0, 10]
			}
		}
	],
	observer: { metrics: ['metric_a'], emit_every: 1 },
	storage: { artifacts_dir: 'runs', metrics: true, events: true },
	visualization: { emit_every: 1 }
};

describe('experiment builder helpers', () => {
	test('discovers scalar schema paths from a plugin-backed config', () => {
		expect(scalarParameterPaths(config)).toEqual([
			{ path: 'seed', label: 'Seed', value: 42, type: 'number' },
			{ path: 'scheduler.t_end', label: 'Scheduler duration', value: 24, type: 'number' },
			{ path: 'solvers[0].params.rate_a', label: 'Rate a', value: 0.6, type: 'number' },
			{
				path: 'solvers[0].params.rate_b',
				label: 'Rate b',
				value: 0.08,
				type: 'number'
			},
			{ path: 'observer.emit_every', label: 'Observer cadence', value: 1, type: 'number' },
			{
				path: 'visualization.emit_every',
				label: 'Visualization cadence',
				value: 1,
				type: 'number'
			}
		]);
	});

	test('includes optional demo pacing controls when present', () => {
		expect(
			scalarParameterPaths({
				...config,
				scheduler: { ...config.scheduler, demo_delay_ms_per_tick: 25 }
			})
		).toContainEqual({
			path: 'scheduler.demo_delay_ms_per_tick',
			label: 'Demo delay per tick',
			value: 25,
			type: 'number'
		});
	});

	test('assigns nested config paths immutably', () => {
		const next = assignConfigPath(config, 'solvers[0].params.rate_a', 0.25);

		expect(next.solvers[0]?.params.rate_a).toBe(0.25);
		expect(config.solvers[0]?.params.rate_a).toBe(0.6);
	});

	test('returns friendly labels and validation messages', () => {
		expect(friendlyLabel('solvers[0].params.rate_a')).toBe('Rate a');
		expect(validateBuilderConfig({ ...config, name: '', solvers: [] })).toEqual([
			'Experiment name is required.',
			'At least one plugin solver is required.'
		]);
	});

	test('validates partial advanced JSON payloads without throwing', () => {
		expect(validateBuilderConfig({})).toEqual([
			'Experiment name is required.',
			'Seed must be an integer.',
			'Duration must be positive.',
			'At least one plugin solver is required.'
		]);
	});
});
