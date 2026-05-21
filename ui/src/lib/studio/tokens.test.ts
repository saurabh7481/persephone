import { describe, expect, test } from 'vitest';

import { contrastRatio, studioPrinciples, studioTokenGroups } from './tokens';

describe('Studio design tokens', () => {
	test('document the product design principles', () => {
		expect(studioPrinciples).toContain('instrument-like');
		expect(studioPrinciples).toContain('technical on demand');
		expect(studioPrinciples.length).toBeGreaterThanOrEqual(6);
	});

	test('keep shell colors accessible for text and focus states', () => {
		expect(
			contrastRatio(studioTokenGroups.light.shellForeground, studioTokenGroups.light.shell)
		).toBeGreaterThan(7);
		expect(
			contrastRatio(studioTokenGroups.dark.shellForeground, studioTokenGroups.dark.shell)
		).toBeGreaterThan(7);
		expect(
			contrastRatio(studioTokenGroups.light.accent, studioTokenGroups.light.surface)
		).toBeGreaterThan(3);
	});
});
