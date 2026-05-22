import { describe, expect, test } from 'vitest';

import { shortcutActionFromEvent, toggleFocusSurface } from './run-focus';

describe('run workbench focus helpers', () => {
	test('toggles focus surfaces without losing intent', () => {
		expect(toggleFocusSurface('none', 'viewport')).toBe('viewport');
		expect(toggleFocusSurface('viewport', 'viewport')).toBe('none');
		expect(toggleFocusSurface('viewport', 'metrics')).toBe('metrics');
		expect(toggleFocusSurface('metrics', 'viewport')).toBe('viewport');
	});

	test('maps keyboard shortcuts and ignores text-entry targets', () => {
		expect(shortcutActionFromEvent({ key: ' ', code: 'Space' })).toBe('toggle_playback');
		expect(shortcutActionFromEvent({ key: 'ArrowLeft' })).toBe('previous_frame');
		expect(shortcutActionFromEvent({ key: 'ArrowRight' })).toBe('next_frame');
		expect(shortcutActionFromEvent({ key: 'f' })).toBe('toggle_viewport_focus');
		expect(shortcutActionFromEvent({ key: 'm' })).toBe('toggle_metric_focus');
		expect(shortcutActionFromEvent({ key: 'Escape' })).toBe('clear_focus');
		expect(shortcutActionFromEvent({ key: 'f', ctrlKey: true })).toBeNull();
		expect(
			shortcutActionFromEvent({
				key: 'f',
				targetTagName: 'input'
			})
		).toBeNull();
		expect(
			shortcutActionFromEvent({
				key: 'm',
				isContentEditable: true
			})
		).toBeNull();
	});
});
