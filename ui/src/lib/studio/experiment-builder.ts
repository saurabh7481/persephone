import type { ExperimentConfig } from '$lib/api-client';

export type ScalarParameterPath = {
	path: string;
	label: string;
	value: string | number | boolean;
	type: 'string' | 'number' | 'boolean';
};

type ParsedPathPart = string | number;

const LABEL_OVERRIDES: Record<string, string> = {
	'scheduler.t_end': 'Scheduler duration',
	'scheduler.demo_delay_ms_per_tick': 'Demo delay per tick',
	'observer.emit_every': 'Observer cadence',
	'visualization.emit_every': 'Visualization cadence'
};

export function scalarParameterPaths(config: ExperimentConfig): ScalarParameterPath[] {
	const paths: ScalarParameterPath[] = [
		scalarPath('seed', config.seed),
		scalarPath('scheduler.t_end', config.scheduler.t_end)
	];

	if (config.scheduler.demo_delay_ms_per_tick !== undefined) {
		paths.push(
			scalarPath('scheduler.demo_delay_ms_per_tick', config.scheduler.demo_delay_ms_per_tick)
		);
	}

	config.solvers.forEach((solver, index) => {
		for (const [key, value] of Object.entries(solver.params)) {
			if (isScalar(value)) {
				paths.push(scalarPath(`solvers[${index}].params.${key}`, value));
			}
		}
	});

	paths.push(scalarPath('observer.emit_every', config.observer.emit_every));
	if (config.visualization?.emit_every !== undefined) {
		paths.push(scalarPath('visualization.emit_every', config.visualization.emit_every));
	}
	return paths;
}

export function assignConfigPath(
	config: ExperimentConfig,
	path: string,
	value: string | number | boolean
): ExperimentConfig {
	const next = structuredClone(config);
	const parts = parsePath(path);
	let cursor: Record<string, unknown> | unknown[] = next as unknown as Record<string, unknown>;
	for (const part of parts.slice(0, -1)) {
		cursor = (cursor as Record<string, unknown> | unknown[])[part as keyof typeof cursor] as
			| Record<string, unknown>
			| unknown[];
	}
	const finalPart = parts.at(-1);
	if (finalPart !== undefined) {
		(cursor as Record<string, unknown> | unknown[])[finalPart as keyof typeof cursor] =
			value as never;
	}
	return next;
}

export function friendlyLabel(path: string): string {
	if (LABEL_OVERRIDES[path]) return LABEL_OVERRIDES[path];
	const leaf =
		path
			.split('.')
			.at(-1)
			?.replace(/\[\d+\]/g, '') ?? path;
	return leaf
		.replace(/^params\./, '')
		.split('_')
		.filter(Boolean)
		.map((part, index) => (index === 0 ? titleCase(part) : part))
		.join(' ');
}

export function validateBuilderConfig(config: Partial<ExperimentConfig>): string[] {
	const errors: string[] = [];
	if (typeof config.name !== 'string' || !config.name.trim()) {
		errors.push('Experiment name is required.');
	}
	if (!Number.isInteger(config.seed)) errors.push('Seed must be an integer.');
	if (typeof config.scheduler?.t_end !== 'number' || config.scheduler.t_end <= 0) {
		errors.push('Duration must be positive.');
	}
	const solvers = Array.isArray(config.solvers) ? config.solvers : [];
	if (solvers.length === 0) errors.push('At least one plugin solver is required.');
	for (const [index, solver] of solvers.entries()) {
		if (typeof solver.plugin !== 'string' || !solver.plugin.trim()) {
			errors.push(`Solver ${index + 1} requires a plugin.`);
		}
	}
	return errors;
}

export function coerceScalarValue(value: string, original: string | number | boolean) {
	if (typeof original === 'number') {
		const numeric = Number(value);
		return Number.isFinite(numeric) ? numeric : original;
	}
	if (typeof original === 'boolean') return value === 'true';
	return value;
}

function scalarPath(path: string, value: string | number | boolean): ScalarParameterPath {
	return {
		path,
		label: friendlyLabel(path),
		value,
		type: typeof value as ScalarParameterPath['type']
	};
}

function isScalar(value: unknown): value is string | number | boolean {
	return ['string', 'number', 'boolean'].includes(typeof value);
}

function parsePath(path: string): ParsedPathPart[] {
	return path.split('.').flatMap((part) => {
		const pieces: ParsedPathPart[] = [];
		const match = /^([^[]+)(?:\[(\d+)])?$/.exec(part);
		if (!match) return [part];
		pieces.push(match[1] ?? part);
		if (match[2] !== undefined) pieces.push(Number(match[2]));
		return pieces;
	});
}

function titleCase(value: string): string {
	return value ? `${value[0]?.toUpperCase()}${value.slice(1)}` : value;
}
