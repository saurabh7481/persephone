export const studioPrinciples = [
	'instrument-like',
	'calm',
	'dense',
	'readable',
	'non-technical default',
	'technical on demand',
	'playback centered'
] as const;

export const studioTokenGroups = {
	light: {
		shell: '#f6f8fb',
		shellForeground: '#172033',
		surface: '#ffffff',
		surfaceRaised: '#f9fbff',
		panel: '#eef3f8',
		border: '#cfd9e6',
		accent: '#0f6b7a',
		accentForeground: '#ffffff',
		warning: '#a85b00',
		success: '#1f7a4d'
	},
	dark: {
		shell: '#101722',
		shellForeground: '#eef4fb',
		surface: '#151f2c',
		surfaceRaised: '#1b2838',
		panel: '#0d131c',
		border: '#344255',
		accent: '#5ac8d8',
		accentForeground: '#061115',
		warning: '#f2b35d',
		success: '#71d29a'
	}
} as const;

export const studioTypography = {
	shellTitle: 'text-sm font-semibold tracking-normal',
	panelTitle: 'text-xs font-semibold uppercase tracking-[0.08em]',
	denseBody: 'text-sm leading-5',
	tableText: 'text-xs leading-5',
	viewportOverlay: 'text-xs font-medium'
} as const;

export const studioSpacing = {
	rail: '3.75rem',
	topbar: '3.5rem',
	contextPanel: '17rem',
	inspector: '20rem',
	dock: '16rem',
	gap: '0.75rem'
} as const;

export const studioRadii = {
	panel: '0.5rem',
	control: '0.375rem',
	viewport: '0.5rem'
} as const;

export function contrastRatio(foreground: string, background: string): number {
	const fg = relativeLuminance(hexToRgb(foreground));
	const bg = relativeLuminance(hexToRgb(background));
	const lighter = Math.max(fg, bg);
	const darker = Math.min(fg, bg);
	return (lighter + 0.05) / (darker + 0.05);
}

function hexToRgb(hex: string): [number, number, number] {
	const normalized = hex.replace('#', '');
	const value = Number.parseInt(normalized, 16);
	return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function relativeLuminance([red, green, blue]: [number, number, number]): number {
	const [r, g, b] = [red, green, blue].map((channel) => {
		const value = channel / 255;
		return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
