import { describe, expect, test } from 'vitest';

import type { MetricRecord, PluginSemantics } from '$lib/api-client';

import { buildMetricDeck, togglePinnedMetric } from './metrics';

const semantics: PluginSemantics[] = [
	{
		name: 'demo',
		version: '0.1.0',
		semantics: {
			metric_schema: {
				infections: {
					name: 'infections',
					label: 'Active infections',
					kind: 'scalar',
					unit: 'people',
					headline: true
				},
				latency: {
					name: 'latency',
					label: 'Network latency',
					kind: 'scalar',
					unit: 'ms',
					headline: true
				},
				throughput: {
					name: 'throughput',
					label: 'Throughput',
					kind: 'scalar',
					unit: 'ops/s'
				}
			}
		}
	}
];

const records: MetricRecord[] = [
	{ t: 1, metric: 'infections', value: 42, warning_threshold: 70, critical_threshold: 90 },
	{ t: 2, metric: 'infections', value: 81, warning_threshold: 70, critical_threshold: 90 },
	{ t: 3, metric: 'infections', value: 96, warning_threshold: 70, critical_threshold: 90 },
	{ t: 1, metric: 'latency', value: 48, warning_threshold: 60, critical_threshold: 90 },
	{ t: 2, metric: 'latency', value: 94, warning_threshold: 60, critical_threshold: 90 },
	{ t: 3, metric: 'latency', value: 72, warning_threshold: 60, critical_threshold: 90 },
	{ t: 1, metric: 'throughput', value: 120 },
	{ t: 2, metric: 'throughput', value: 121 },
	{ t: 3, metric: 'throughput', value: 122 },
	{ t: 1, metric: 'load', value: 10 },
	{ t: 2, metric: 'load', value: 12 },
	{ t: 3, metric: 'load', value: 15 },
	{ t: 1, metric: 'scheduler.tick', value: 1 }
];

describe('metric deck helpers', () => {
	test('ranks pinned and headline metrics while classifying attention states', () => {
		const deck = buildMetricDeck({
			records,
			pluginSemantics: semantics,
			selectedTime: 3,
			pinnedMetrics: new Set(['throughput'])
		});

		expect(deck.map((item) => item.metric)).toEqual([
			'throughput',
			'infections',
			'latency',
			'load'
		]);
		expect(deck.find((item) => item.metric === 'infections')?.attention).toBe('critical');
		expect(deck.find((item) => item.metric === 'latency')?.attention).toBe('improving');
		expect(deck.find((item) => item.metric === 'load')?.attention).toBe('rising_concern');
		expect(deck.find((item) => item.metric === 'throughput')?.pinned).toBe(true);
		expect(deck.find((item) => item.metric === 'infections')?.headline).toBe(true);
		expect(deck.find((item) => item.metric === 'infections')?.label).toBe('Active infections');
		expect(deck.find((item) => item.metric === 'load')?.label).toBe('Load');
	});

	test('toggles pinned metrics without mutating the input set', () => {
		const initial = new Set(['infections']);
		const withLatency = togglePinnedMetric(initial, 'latency');
		const withoutInfections = togglePinnedMetric(withLatency, 'infections');

		expect([...initial]).toEqual(['infections']);
		expect([...withLatency]).toEqual(['infections', 'latency']);
		expect([...withoutInfections]).toEqual(['latency']);
	});
});
