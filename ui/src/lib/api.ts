import type { ExperimentConfig, MetricRecord, SweepValue } from './api-client';

export { PersephoneApiClient as PersephoneApi, apiBaseUrl, parseJsonResponse } from './api-client';
export type * from './api-client';

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
