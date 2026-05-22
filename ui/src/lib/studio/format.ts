export type NumberFormatOptions = {
	compact?: boolean;
	minimumFractionDigits?: number;
	maximumFractionDigits?: number;
};

export type MetricFormatOptions = NumberFormatOptions & {
	unit?: string | null;
};

export function formatNumber(
	value: number | null | undefined,
	{
		compact = false,
		minimumFractionDigits = 0,
		maximumFractionDigits = 2
	}: NumberFormatOptions = {}
): string {
	if (value == null || !Number.isFinite(value)) return '-';
	return new Intl.NumberFormat('en-US', {
		notation: compact ? 'compact' : 'standard',
		minimumFractionDigits,
		maximumFractionDigits
	}).format(value);
}

export function formatMetricValue(
	value: number | null | undefined,
	unit: string | null = null,
	options: NumberFormatOptions = {}
): string {
	const formatted = formatNumber(value, options);
	if (formatted === '-') return formatted;
	return unit ? `${formatted} ${unit}` : formatted;
}

export function formatPercent(
	value: number | null | undefined,
	{
		signed = false,
		maximumFractionDigits = 1
	}: { signed?: boolean; maximumFractionDigits?: number } = {}
): string {
	if (value == null || !Number.isFinite(value)) return '-';
	const formatted = new Intl.NumberFormat('en-US', {
		style: 'percent',
		signDisplay: signed ? 'always' : 'auto',
		maximumFractionDigits
	}).format(value);
	return formatted.replace('+', signed ? '+' : '');
}

export function formatDelta(
	value: number | null | undefined,
	{ unit = null, maximumFractionDigits = 2 }: MetricFormatOptions = {}
): string {
	if (value == null || !Number.isFinite(value)) return '-';
	const formatted = new Intl.NumberFormat('en-US', {
		signDisplay: 'always',
		maximumFractionDigits
	}).format(value);
	return unit ? `${formatted} ${unit}` : formatted;
}

export function formatTimeLabel(
	value: number | null | undefined,
	{
		prefix = 't=',
		maximumFractionDigits = 2
	}: { prefix?: string; maximumFractionDigits?: number } = {}
): string {
	if (value == null || !Number.isFinite(value)) return `${prefix}-`;
	return `${prefix}${formatNumber(value, { maximumFractionDigits })}`;
}

export function humanizeIdentifier(value: string | null | undefined): string {
	if (!value) return '';
	return value
		.replace(/[._-]+/g, ' ')
		.replace(/\s+/g, ' ')
		.trim()
		.replace(/^\w/, (character) => character.toUpperCase());
}

export function formatUnknownValue(value: unknown, unit: string | null = null): string {
	if (value == null) return '-';
	if (typeof value === 'number') return formatMetricValue(value, unit);
	if (typeof value === 'boolean') return value ? 'Yes' : 'No';
	return unit ? `${String(value)} ${unit}` : String(value);
}
