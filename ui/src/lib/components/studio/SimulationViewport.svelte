<script lang="ts">
	import { onMount } from 'svelte';

	import type { SimulationFrame } from '$lib/api-client';
	import type { PlaybackMode, PlaybackStatus, SelectedPlaybackObject } from '$lib/studio/playback';
	import {
		describeGraphObject,
		fieldCellFromPoint,
		graphHitTest,
		graphLayout,
		normalizeViewport,
		renderSimulationFrame,
		type FieldRenderOptions,
		type GraphRenderOptions,
		type GraphRenderMode
	} from '$lib/studio/renderers';

	type ViewKind =
		| 'network'
		| 'positioned_graph'
		| 'map_network'
		| 'matrix'
		| 'table'
		| 'timeline'
		| 'heatmap'
		| 'hierarchy';

	let {
		frame = null,
		mode = 'idle',
		status = 'idle',
		speed = 1,
		bufferedFrames = 0,
		viewKind = 'heatmap',
		viewLabel = 'Viewport',
		selectedObject = null,
		onSelect
	}: {
		frame?: SimulationFrame | null;
		mode?: PlaybackMode;
		status?: PlaybackStatus;
		speed?: number;
		bufferedFrames?: number;
		viewKind?: ViewKind;
		viewLabel?: string;
		selectedObject?: SelectedPlaybackObject | null;
		onSelect?: (object: SelectedPlaybackObject | null) => void;
	} = $props();

	let canvas = $state<HTMLCanvasElement | null>(null);
	let viewportElement = $state<HTMLDivElement | null>(null);
	let width = $state(1);
	let height = $state(1);
	let hoverLabel = $state('');
	let palette = $state('');
	let autoscale = $state(true);
	let opacity = $state(1);
	let manualMin = $state('');
	let manualMax = $state('');
	let graphSearch = $state('');
	let edgeThreshold = $state('');
	let aggregateGroups = $state(false);
	let zoom = $state(1);
	let panX = $state(0);
	let panY = $state(0);
	let draggingGraph = $state(false);
	let renderHandle = 0;
	let pointerAnchorX = 0;
	let pointerAnchorY = 0;
	let pointerPanX = 0;
	let pointerPanY = 0;
	let movedDuringDrag = false;

	const isFieldFrame = $derived(frame?.kind === 'field');
	const isGraphFrame = $derived(frame?.kind === 'graph');
	const paletteValue = $derived(
		palette ||
			(typeof frame?.visualization.palette === 'string' ? frame.visualization.palette : 'viridis')
	);
	const fieldOptions = $derived<FieldRenderOptions>({
		palette: paletteValue,
		autoscale,
		min: manualMin === '' ? undefined : Number(manualMin),
		max: manualMax === '' ? undefined : Number(manualMax),
		opacity
	});
	const graphOptions = $derived<GraphRenderOptions>({
		mode: graphModeFor(viewKind, frame),
		search: graphSearch,
		edgeThreshold: edgeThreshold === '' ? undefined : Number(edgeThreshold),
		aggregateGroups,
		zoom,
		panX,
		panY
	});

	onMount(() => {
		if (!viewportElement) return;
		const observer = new ResizeObserver(([entry]) => {
			width = Math.max(1, Math.floor(entry.contentRect.width));
			height = Math.max(1, Math.floor(entry.contentRect.height));
			scheduleRender();
		});
		width = Math.max(1, Math.floor(viewportElement.clientWidth));
		height = Math.max(1, Math.floor(viewportElement.clientHeight));
		observer.observe(viewportElement);
		scheduleRender();
		return () => {
			observer.disconnect();
			if (renderHandle) cancelAnimationFrame(renderHandle);
		};
	});

	$effect(() => {
		scheduleRenderFor(frame, selectedObject, width, height, fieldOptions, graphOptions);
	});

	function scheduleRenderFor(
		_frame: SimulationFrame | null,
		_selectedObject: SelectedPlaybackObject | null,
		_width: number,
		_height: number,
		_fieldOptions: FieldRenderOptions,
		_graphOptions: GraphRenderOptions
	) {
		const dependencies = [_frame, _selectedObject, _width, _height, _fieldOptions, _graphOptions];
		if (!dependencies.length) return;
		scheduleRender();
	}

	function scheduleRender() {
		if (!canvas || !frame || renderHandle) return;
		renderHandle = requestAnimationFrame(() => {
			renderHandle = 0;
			paint();
		});
	}

	function paint() {
		if (!canvas || !frame) return;
		const context = canvas.getContext('2d');
		if (!context) return;
		const viewport = normalizeViewport(width, height, globalThis.devicePixelRatio ?? 1);
		const physicalWidth = Math.floor(viewport.width * viewport.dpr);
		const physicalHeight = Math.floor(viewport.height * viewport.dpr);
		if (canvas.width !== physicalWidth || canvas.height !== physicalHeight) {
			canvas.width = physicalWidth;
			canvas.height = physicalHeight;
		}
		context.setTransform(viewport.dpr, 0, 0, viewport.dpr, 0, 0);
		renderSimulationFrame(context, frame, viewport, fieldOptions, selectedObject, graphOptions);
	}

	function selectAtPointer(event: MouseEvent | PointerEvent) {
		const object = objectAtPointer(event);
		onSelect?.(object);
	}

	function hoverAtPointer(event: PointerEvent) {
		if (draggingGraph) return;
		const object = objectAtPointer(event);
		hoverLabel = describeObject(object);
	}

	function clearHover() {
		hoverLabel = '';
	}

	function objectAtPointer(event: MouseEvent | PointerEvent): SelectedPlaybackObject | null {
		if (!canvas || !frame) return null;
		const rect = canvas.getBoundingClientRect();
		const x = event.clientX - rect.left;
		const y = event.clientY - rect.top;
		const viewport = normalizeViewport(rect.width, rect.height, globalThis.devicePixelRatio ?? 1);
		if (frame.kind === 'field') return fieldCellFromPoint(frame, viewport, x, y);
		return graphHitTest(graphLayout(frame, viewport, graphOptions), x, y);
	}

	function describeObject(object: SelectedPlaybackObject | null): string {
		if (!object) return '';
		if (object.kind === 'field-cell') {
			const cell = object as SelectedPlaybackObject & {
				row?: number;
				column?: number;
				value?: number | null;
			};
			const value = typeof cell.value === 'number' ? cell.value.toPrecision(4) : '-';
			return `cell ${cell.row},${cell.column} · ${value}`;
		}
		if (frame?.kind === 'graph') {
			const viewport = normalizeViewport(width, height, globalThis.devicePixelRatio ?? 1);
			return describeGraphObject(graphLayout(frame, viewport, graphOptions), object);
		}
		return object.id;
	}

	function handlePointerDown(event: PointerEvent) {
		if (!isGraphFrame || !canvas) return;
		draggingGraph = true;
		movedDuringDrag = false;
		pointerAnchorX = event.clientX;
		pointerAnchorY = event.clientY;
		pointerPanX = panX;
		pointerPanY = panY;
		canvas.setPointerCapture(event.pointerId);
	}

	function handlePointerMove(event: PointerEvent) {
		if (!draggingGraph) {
			hoverAtPointer(event);
			return;
		}
		movedDuringDrag =
			movedDuringDrag ||
			Math.hypot(event.clientX - pointerAnchorX, event.clientY - pointerAnchorY) > 3;
		panX = pointerPanX + (event.clientX - pointerAnchorX);
		panY = pointerPanY + (event.clientY - pointerAnchorY);
		scheduleRender();
	}

	function handlePointerUp(event: PointerEvent) {
		if (!draggingGraph || !canvas) {
			selectAtPointer(event);
			return;
		}
		draggingGraph = false;
		canvas.releasePointerCapture(event.pointerId);
		if (!movedDuringDrag) selectAtPointer(event);
	}

	function handleWheel(event: WheelEvent) {
		if (!isGraphFrame) return;
		event.preventDefault();
		const multiplier = event.deltaY < 0 ? 1.08 : 0.92;
		zoom = clamp(zoom * multiplier, 0.6, 6);
	}

	function nudgeZoom(delta: number) {
		zoom = clamp(zoom + delta, 0.6, 6);
	}

	function resetGraphViewport() {
		graphSearch = '';
		edgeThreshold = '';
		aggregateGroups = false;
		zoom = 1;
		panX = 0;
		panY = 0;
	}

	function graphModeFor(
		currentView: ViewKind,
		currentFrame: SimulationFrame | null
	): GraphRenderMode | undefined {
		if (!currentFrame || currentFrame.kind !== 'graph') return undefined;
		if (
			currentView === 'network' ||
			currentView === 'positioned_graph' ||
			currentView === 'map_network' ||
			currentView === 'matrix'
		) {
			return currentView;
		}
		return undefined;
	}

	function clamp(value: number, min: number, max: number): number {
		return Math.min(max, Math.max(min, value));
	}
</script>

<div bind:this={viewportElement} class="simulation-viewport" data-status={status}>
	{#if frame}
		<canvas
			bind:this={canvas}
			class="simulation-viewport-canvas"
			aria-label="Rendered simulation frame"
			onclick={!isGraphFrame ? selectAtPointer : undefined}
			onpointerdown={handlePointerDown}
			onpointermove={handlePointerMove}
			onpointerup={handlePointerUp}
			onpointerleave={clearHover}
			onwheel={handleWheel}
		></canvas>

		<div class="simulation-viewport-hud" aria-live="polite">
			<div>
				<p class="studio-eyebrow">{mode} · {status}</p>
				<h2>{viewLabel}</h2>
				<p>
					{frame.frame_id} · t={frame.t.toFixed(2)} · {speed}x · Frame buffer {bufferedFrames}
				</p>
			</div>
			{#if hoverLabel}
				<p class="simulation-viewport-hover">{hoverLabel}</p>
			{/if}
		</div>

		{#if isFieldFrame}
			<div class="simulation-viewport-controls" aria-label="Field visualization controls">
				<label>
					<span>Palette</span>
					<select bind:value={palette}>
						<option value="">Frame</option>
						<option value="viridis">Viridis</option>
						<option value="inferno">Inferno</option>
						<option value="magma">Magma</option>
						<option value="gray">Gray</option>
					</select>
				</label>
				<label class="simulation-viewport-checkbox">
					<input type="checkbox" bind:checked={autoscale} />
					<span>Autoscale</span>
				</label>
				<label>
					<span>Min</span>
					<input bind:value={manualMin} type="number" step="any" disabled={autoscale} />
				</label>
				<label>
					<span>Max</span>
					<input bind:value={manualMax} type="number" step="any" disabled={autoscale} />
				</label>
				<label>
					<span>Opacity</span>
					<input bind:value={opacity} type="range" min="0.1" max="1" step="0.05" />
				</label>
			</div>
		{/if}

		{#if isGraphFrame}
			<div class="simulation-viewport-controls" aria-label="Graph visualization controls">
				<label class="min-w-[12rem]">
					<span>Search and highlight</span>
					<input bind:value={graphSearch} placeholder="node label, group, state" />
				</label>
				<label>
					<span>Edge filter</span>
					<input bind:value={edgeThreshold} type="range" min="0" max="1" step="0.05" />
					<small
						>{edgeThreshold === '' ? 'all edges' : `>= ${Number(edgeThreshold).toFixed(2)}`}</small
					>
				</label>
				<label class="simulation-viewport-checkbox">
					<input type="checkbox" bind:checked={aggregateGroups} />
					<span>Cluster groups</span>
				</label>
				<div class="simulation-viewport-zoom">
					<button type="button" onclick={() => nudgeZoom(-0.2)} aria-label="Zoom out">-</button>
					<span>{zoom.toFixed(1)}x</span>
					<button type="button" onclick={() => nudgeZoom(0.2)} aria-label="Zoom in">+</button>
					<button type="button" onclick={resetGraphViewport}>Reset</button>
				</div>
			</div>
		{/if}
	{:else if status === 'buffering'}
		<div class="studio-viewport-empty">
			<div>
				<p class="studio-eyebrow">{mode} · buffering</p>
				<h2>Waiting for frames</h2>
				<p>The viewport will draw as soon as the first simulation frame arrives.</p>
			</div>
		</div>
	{:else if status === 'error'}
		<div class="studio-viewport-empty" role="alert">
			<div>
				<p class="studio-eyebrow">{mode} · error</p>
				<h2>Frame renderer unavailable</h2>
				<p>Playback state is still available in the frame buffer and logs.</p>
			</div>
		</div>
	{:else}
		<div class="studio-viewport-empty">
			<div>
				<p class="studio-eyebrow">{mode} · {status}</p>
				<h2>No frame selected</h2>
				<p>Load a replay or live run to inspect field and graph frames.</p>
			</div>
		</div>
	{/if}
</div>
