export type StudioTheme = 'light' | 'dark';

export const STUDIO_THEME_STORAGE_KEY = 'persephone-studio-theme';

export function storedStudioTheme(value: string | null): StudioTheme | null {
	return value === 'light' || value === 'dark' ? value : null;
}

export function resolveStudioTheme(storedTheme: string | null, prefersDark: boolean): StudioTheme {
	return storedStudioTheme(storedTheme) ?? (prefersDark ? 'dark' : 'light');
}

export function applyStudioTheme(
	theme: StudioTheme,
	root: HTMLElement = document.documentElement
): void {
	root.classList.toggle('dark', theme === 'dark');
	root.dataset.theme = theme;
}
