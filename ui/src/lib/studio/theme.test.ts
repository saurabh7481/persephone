import { describe, expect, test } from 'vitest';

import { applyStudioTheme, resolveStudioTheme, storedStudioTheme, type StudioTheme } from './theme';

describe('studio theme helpers', () => {
	test('resolves stored and preferred themes', () => {
		expect(storedStudioTheme('light')).toBe('light');
		expect(storedStudioTheme('dark')).toBe('dark');
		expect(storedStudioTheme('system')).toBeNull();
		expect(resolveStudioTheme('dark', false)).toBe('dark');
		expect(resolveStudioTheme(null, true)).toBe('dark');
		expect(resolveStudioTheme(null, false)).toBe('light');
	});

	test('applies the dark class and theme dataset to the root element', () => {
		const classes = new Set<string>();
		const root = {
			dataset: {} as DOMStringMap,
			classList: {
				toggle(name: string, force?: boolean) {
					const shouldAdd = force ?? !classes.has(name);
					if (shouldAdd) classes.add(name);
					else classes.delete(name);
				},
				contains(name: string) {
					return classes.has(name);
				}
			}
		} as unknown as HTMLElement;

		applyStudioTheme('dark', root);
		expect(root.classList.contains('dark')).toBe(true);
		expect(root.dataset.theme).toBe('dark');

		applyStudioTheme('light' satisfies StudioTheme, root);
		expect(root.classList.contains('dark')).toBe(false);
		expect(root.dataset.theme).toBe('light');
	});
});
