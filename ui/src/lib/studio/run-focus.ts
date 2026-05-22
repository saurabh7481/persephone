export type FocusSurface = 'none' | 'viewport' | 'metrics';

export type ShortcutAction =
	| 'toggle_playback'
	| 'previous_frame'
	| 'next_frame'
	| 'toggle_viewport_focus'
	| 'toggle_metric_focus'
	| 'clear_focus';

export type ShortcutEventLike = {
	key: string;
	code?: string;
	ctrlKey?: boolean;
	metaKey?: boolean;
	altKey?: boolean;
	targetTagName?: string | null;
	isContentEditable?: boolean;
};

export function toggleFocusSurface(
	current: FocusSurface,
	target: Exclude<FocusSurface, 'none'>
): FocusSurface {
	return current === target ? 'none' : target;
}

export function shortcutActionFromEvent(event: ShortcutEventLike): ShortcutAction | null {
	if (event.ctrlKey || event.metaKey || event.altKey) return null;
	if (isTypingTarget(event)) return null;

	if (event.key === ' ' || event.code === 'Space') return 'toggle_playback';
	if (event.key === 'ArrowLeft') return 'previous_frame';
	if (event.key === 'ArrowRight') return 'next_frame';
	if (event.key === 'Escape') return 'clear_focus';

	const key = event.key.toLowerCase();
	if (key === 'f') return 'toggle_viewport_focus';
	if (key === 'm') return 'toggle_metric_focus';
	return null;
}

function isTypingTarget(event: ShortcutEventLike): boolean {
	if (event.isContentEditable) return true;
	const tag = event.targetTagName?.toLowerCase();
	return tag === 'input' || tag === 'textarea' || tag === 'select';
}
