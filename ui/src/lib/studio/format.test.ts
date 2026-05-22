import { describe, expect, test } from 'vitest';

import {
	formatDelta,
	formatMetricValue,
	formatNumber,
	formatPercent,
	formatTimeLabel,
	humanizeIdentifier
} from './format';

describe('studio presentation formatting', () => {
	test('formats headline and compact numeric values with bounded precision', () => {
		expect(formatNumber(21.3576436013167)).toBe('21.36');
		expect(formatNumber(1200)).toBe('1,200');
		expect(formatNumber(9876543, { compact: true, maximumFractionDigits: 1 })).toBe('9.9M');
		expect(formatNumber(0.333333, { maximumFractionDigits: 3 })).toBe('0.333');
	});

	test('formats metric values with units and fallback output', () => {
		expect(formatMetricValue(21.3576436013167, 'idx')).toBe('21.36 idx');
		expect(formatMetricValue(0.8, 'idx', { maximumFractionDigits: 3 })).toBe('0.8 idx');
		expect(formatMetricValue(null, 'idx')).toBe('-');
	});

	test('formats deltas and percentages consistently', () => {
		expect(formatDelta(2.314, { unit: 'idx' })).toBe('+2.31 idx');
		expect(formatDelta(-2.314, { unit: 'idx' })).toBe('-2.31 idx');
		expect(formatPercent(0.1279)).toBe('12.8%');
		expect(formatPercent(-0.0984, { signed: true })).toBe('-9.8%');
	});

	test('formats time labels and humanizes machine identifiers', () => {
		expect(formatTimeLabel(5)).toBe('t=5');
		expect(formatTimeLabel(5.125)).toBe('t=5.13');
		expect(humanizeIdentifier('delivery_risk_index')).toBe('Delivery risk index');
		expect(humanizeIdentifier('scheduler.wall_time_ms')).toBe('Scheduler wall time ms');
	});
});
