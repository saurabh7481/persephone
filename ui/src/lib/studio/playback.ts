import { get, writable, type Readable } from 'svelte/store';

import type { FrameListEntry, SimulationFrame } from '$lib/api-client';

export type PlaybackMode = 'idle' | 'live' | 'replay';
export type PlaybackStatus = 'idle' | 'buffering' | 'playing' | 'paused' | 'completed' | 'error';

export type SelectedPlaybackObject = {
	kind: 'field-cell' | 'graph-node' | 'graph-edge' | 'frame' | 'metric';
	id: string;
};

export type PlaybackState = {
	mode: PlaybackMode;
	status: PlaybackStatus;
	runId: string | null;
	currentTime: number;
	speed: number;
	frameBuffer: SimulationFrame[];
	selectedFrameId: string | null;
	selectedObject: SelectedPlaybackObject | null;
	error: string | null;
};

export type LiveFrameHandlers = {
	frame: (frame: SimulationFrame) => void;
	status: (status: string) => void;
	error: (message: string) => void;
	complete: () => void;
};

export type PlaybackSource = {
	loadReplayFrames?: (runId: string) => Promise<SimulationFrame[]>;
	connectLiveFrames?: (runId: string, handlers: LiveFrameHandlers) => () => void;
};

export type PlaybackStore = Readable<PlaybackState> & {
	snapshot: () => PlaybackState;
	loadReplay: (runId: string) => Promise<void>;
	connectLive: (runId: string) => void;
	play: () => void;
	pause: () => void;
	setSpeed: (speed: number) => void;
	scrubTo: (time: number) => void;
	jumpToStart: () => void;
	jumpToEnd: () => void;
	selectFrame: (frameId: string | null) => void;
	selectObject: (object: SelectedPlaybackObject | null) => void;
	destroy: () => void;
};

const initialState: PlaybackState = {
	mode: 'idle',
	status: 'idle',
	runId: null,
	currentTime: 0,
	speed: 1,
	frameBuffer: [],
	selectedFrameId: null,
	selectedObject: null,
	error: null
};

export function createPlaybackStore({
	source,
	maxBufferedFrames = 240
}: {
	source: PlaybackSource;
	maxBufferedFrames?: number;
}): PlaybackStore {
	const state = writable<PlaybackState>(initialState);
	let disconnectLive: (() => void) | null = null;

	function setFrames(frames: SimulationFrame[], mode: PlaybackMode) {
		const ordered = orderFrames(frames);
		state.update((current) => ({
			...current,
			mode,
			status: ordered.length ? 'paused' : 'idle',
			frameBuffer: ordered.slice(-maxBufferedFrames),
			currentTime: ordered[0]?.t ?? 0,
			selectedFrameId: ordered[0]?.frame_id ?? null,
			error: null
		}));
	}

	function appendFrame(frame: SimulationFrame) {
		state.update((current) => {
			const frameBuffer = orderFrames([...current.frameBuffer, frame]).slice(-maxBufferedFrames);
			return {
				...current,
				frameBuffer,
				currentTime: frame.t,
				selectedFrameId: frame.frame_id,
				error: null
			};
		});
	}

	return {
		subscribe: state.subscribe,
		snapshot: () => get(state),
		async loadReplay(runId: string) {
			state.update((current) => ({
				...current,
				mode: 'replay',
				status: 'buffering',
				runId,
				error: null
			}));
			try {
				const frames = await source.loadReplayFrames?.(runId);
				setFrames(frames ?? [], 'replay');
			} catch (error) {
				state.update((current) => ({
					...current,
					status: 'error',
					error: error instanceof Error ? error.message : 'Unable to load replay frames.'
				}));
			}
		},
		connectLive(runId: string) {
			disconnectLive?.();
			state.set({ ...initialState, mode: 'live', status: 'buffering', runId });
			disconnectLive =
				source.connectLiveFrames?.(runId, {
					frame: appendFrame,
					status(status) {
						if (status === 'completed') {
							state.update((current) => ({
								...current,
								mode: 'replay',
								status: 'completed'
							}));
						}
					},
					error(message) {
						state.update((current) => ({ ...current, status: 'error', error: message }));
					},
					complete() {
						state.update((current) => ({ ...current, mode: 'replay', status: 'completed' }));
					}
				}) ?? null;
		},
		play() {
			state.update((current) => ({
				...current,
				status: current.frameBuffer.length ? 'playing' : 'buffering'
			}));
		},
		pause() {
			state.update((current) => ({ ...current, status: 'paused' }));
		},
		setSpeed(speed: number) {
			state.update((current) => ({ ...current, speed: clampSpeed(speed) }));
		},
		scrubTo(time: number) {
			state.update((current) => {
				const selected = nearestFrame(current.frameBuffer, time);
				return {
					...current,
					currentTime: selected?.t ?? time,
					selectedFrameId: selected?.frame_id ?? current.selectedFrameId
				};
			});
		},
		jumpToStart() {
			const firstFrame = get(state).frameBuffer[0];
			if (firstFrame) this.scrubTo(firstFrame.t);
		},
		jumpToEnd() {
			const frames = get(state).frameBuffer;
			const lastFrame = frames.at(-1);
			if (lastFrame) this.scrubTo(lastFrame.t);
		},
		selectFrame(frameId: string | null) {
			state.update((current) => {
				const frame = current.frameBuffer.find((candidate) => candidate.frame_id === frameId);
				return {
					...current,
					selectedFrameId: frameId,
					currentTime: frame?.t ?? current.currentTime
				};
			});
		},
		selectObject(object: SelectedPlaybackObject | null) {
			state.update((current) => ({ ...current, selectedObject: object }));
		},
		destroy() {
			disconnectLive?.();
			disconnectLive = null;
		}
	};
}

export function playbackSourceFromApi(api: {
	listFrames: (
		runId: string,
		options?: { maxCount?: number }
	) => Promise<{ frames: FrameListEntry[] }>;
	getFrame: (runId: string, frameId: string) => Promise<SimulationFrame>;
	frameStreamUrl: (runId: string) => string;
}): PlaybackSource {
	return {
		async loadReplayFrames(runId: string) {
			const listed = await api.listFrames(runId, { maxCount: 500 });
			return Promise.all(listed.frames.map((frame) => api.getFrame(runId, frame.frame_id)));
		},
		connectLiveFrames(runId: string, handlers: LiveFrameHandlers) {
			const stream = new EventSource(api.frameStreamUrl(runId));
			stream.addEventListener('frame', (event) => {
				handlers.frame(JSON.parse((event as MessageEvent).data) as SimulationFrame);
			});
			stream.addEventListener('status', (event) => {
				const payload = JSON.parse((event as MessageEvent).data) as { status?: string };
				handlers.status(payload.status ?? 'completed');
			});
			stream.addEventListener('error', (event) => {
				if ('data' in event && typeof event.data === 'string') {
					const payload = JSON.parse(event.data) as { message?: string };
					handlers.error(payload.message ?? 'Frame stream error.');
				}
			});
			stream.onerror = () => {
				handlers.complete();
				stream.close();
			};
			return () => stream.close();
		}
	};
}

function orderFrames(frames: SimulationFrame[]): SimulationFrame[] {
	return [...frames].sort((left, right) => left.t - right.t || left.tick - right.tick);
}

function nearestFrame(frames: SimulationFrame[], time: number): SimulationFrame | undefined {
	return frames.reduce<SimulationFrame | undefined>((nearest, frame) => {
		if (!nearest) return frame;
		return Math.abs(frame.t - time) < Math.abs(nearest.t - time) ? frame : nearest;
	}, undefined);
}

function clampSpeed(speed: number): number {
	if (!Number.isFinite(speed)) return 1;
	return Math.min(8, Math.max(0.25, speed));
}
