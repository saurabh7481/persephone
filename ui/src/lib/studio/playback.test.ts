import { describe, expect, test, vi } from 'vitest';

import { createPlaybackStore, type PlaybackSource } from './playback';
import type { SimulationFrame } from '$lib/api-client';

const frameA: SimulationFrame = {
	kind: 'field',
	frame_id: 'frame-a',
	t: 1,
	tick: 1,
	solver_id: 'solver',
	source: 'replay',
	field: 'temperature',
	shape: [1, 1],
	dtype: 'float64',
	bounds: { min: 0, max: 1 },
	units: 'temperature',
	visualization: {},
	values: [0.4]
};

const frameB: SimulationFrame = {
	...frameA,
	frame_id: 'frame-b',
	t: 2,
	tick: 2,
	values: [0.8]
};

function current(store: ReturnType<typeof createPlaybackStore>) {
	let value = store.snapshot();
	const unsubscribe = store.subscribe((state) => {
		value = state;
	});
	unsubscribe();
	return value;
}

describe('playback store', () => {
	test('loads replay frames and supports transport-independent controls', async () => {
		const source: PlaybackSource = {
			loadReplayFrames: vi.fn(async () => [frameA, frameB])
		};
		const store = createPlaybackStore({ source });

		await store.loadReplay('run-a');
		store.play();
		store.setSpeed(2);
		store.scrubTo(2);
		store.selectObject({ kind: 'field-cell', id: '0,0' });

		expect(source.loadReplayFrames).toHaveBeenCalledWith('run-a');
		expect(current(store)).toMatchObject({
			mode: 'replay',
			status: 'playing',
			currentTime: 2,
			speed: 2,
			selectedFrameId: 'frame-b',
			selectedObject: { kind: 'field-cell', id: '0,0' }
		});
	});

	test('buffers live frames while local pause keeps backend stream open', () => {
		let receiveFrame: ((frame: SimulationFrame) => void) | undefined;
		let complete: (() => void) | undefined;
		const disconnect = vi.fn();
		const source: PlaybackSource = {
			connectLiveFrames: vi.fn((_runId, handlers) => {
				receiveFrame = handlers.frame;
				complete = handlers.complete;
				return disconnect;
			})
		};
		const store = createPlaybackStore({ source, maxBufferedFrames: 1 });

		store.connectLive('run-a');
		store.pause();
		receiveFrame?.(frameA);
		receiveFrame?.(frameB);

		expect(current(store)).toMatchObject({
			mode: 'live',
			status: 'paused',
			frameBuffer: [frameB],
			selectedFrameId: 'frame-b'
		});
		expect(disconnect).not.toHaveBeenCalled();

		complete?.();
		expect(current(store).mode).toBe('replay');
		expect(current(store).status).toBe('completed');
		store.destroy();
		expect(disconnect).toHaveBeenCalledOnce();
	});

	test('jump controls choose frame bounds', async () => {
		const store = createPlaybackStore({
			source: {
				loadReplayFrames: async () => [frameA, frameB]
			}
		});

		await store.loadReplay('run-a');
		store.jumpToEnd();
		expect(current(store).currentTime).toBe(2);
		store.jumpToStart();
		expect(current(store).currentTime).toBe(1);
	});
});
