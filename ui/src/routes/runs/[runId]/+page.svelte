<script lang="ts">
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import {
		AlertCircle,
		CirclePause,
		CirclePlay,
		Maximize2,
		Minimize2,
		Rewind,
		SkipBack,
		SkipForward
	} from '@lucide/svelte';

	import {
		PersephoneApi,
		compareMetricSummary,
		type EventRecord,
		type ExplanationResponse,
		type FieldArtifactSummary,
		type MetricRecord,
		type PluginSemantics,
		type RunSummary
	} from '$lib/api';
	import MetricTimeline from '$lib/components/MetricTimeline.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { MetricDeck, SimulationViewport, StudioPanel } from '$lib/components/studio';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Table from '$lib/components/ui/table';
	import * as Tabs from '$lib/components/ui/tabs';
	import { createPlaybackStore, playbackSourceFromApi } from '$lib/studio/playback';
	import {
		artifactSummaries,
		browseFrameEntities,
		fieldCellInspection,
		graphEdgeInspection,
		graphNodeInspection,
		runInspection
	} from '$lib/studio/inspector';
	import { buildMetricDeck, togglePinnedMetric, type MetricDeckItem } from '$lib/studio/metrics';
	import {
		extractMilestones,
		milestonePlaybackTarget,
		recentChangeCards,
		type NarrativeMilestone
	} from '$lib/studio/narrative';
	import {
		shortcutActionFromEvent,
		toggleFocusSurface,
		type FocusSurface
	} from '$lib/studio/run-focus';
	import {
		formatMetricValue as formatDisplayMetricValue,
		formatNumber,
		formatTimeLabel,
		formatUnknownValue,
		humanizeIdentifier
	} from '$lib/studio/format';
	import {
		availableViews,
		chooseDefaultView,
		standardViews,
		type StandardViewKind
	} from '$lib/studio/views';

	let { data }: { data: { runId: string } } = $props();
	const api = new PersephoneApi();
	const playback = createPlaybackStore({ source: playbackSourceFromApi(api) });

	let run = $state<RunSummary | null>(null);
	let metrics = $state<MetricRecord[]>([]);
	let events = $state<EventRecord[]>([]);
	let fieldArtifacts = $state<FieldArtifactSummary[]>([]);
	let error = $state('');
	let streamState = $state<'idle' | 'connected' | 'closed'>('idle');
	let selectedView = $state<StandardViewKind | null>(null);
	let selectedViewLocked = $state(false);
	let activeDockTab = $state('metrics');
	let focusSurface = $state<FocusSurface>('none');
	let pinnedMetrics = $state<string[]>([]);
	let expandedMetrics = $state<string[]>([]);
	let focusedMetricId = $state<string | null>(null);
	let runExplanation = $state<ExplanationResponse | null>(null);
	let frameExplanation = $state<ExplanationResponse | null>(null);
	let selectionExplanation = $state<ExplanationResponse | null>(null);
	let runExplanationLoading = $state(false);
	let frameExplanationLoading = $state(false);
	let selectionExplanationLoading = $state(false);
	let loadedFrameExplanationKey = $state('');
	let loadedSelectionExplanationKey = $state('');

	const summary = $derived(compareMetricSummary(metrics));
	const selectedFrame = $derived(
		$playback.frameBuffer.find((frame) => frame.frame_id === $playback.selectedFrameId) ?? null
	);
	const pluginSemantics = $derived<PluginSemantics[]>(run?.plugin_semantics ?? []);
	const recommendedView = $derived(
		chooseDefaultView({
			frame: selectedFrame ?? $playback.frameBuffer[0] ?? null,
			pluginSemantics
		})
	);
	const viewOptions = $derived(
		availableViews({
			frame: selectedFrame ?? $playback.frameBuffer[0] ?? null,
			pluginSemantics
		})
	);
	const currentView = $derived(
		viewOptions.find((view) => view.kind === selectedView) ??
			standardViews.find((view) => view.kind === recommendedView.kind) ??
			recommendedView
	);
	const currentViewSummary = $derived(
		currentView.kind === recommendedView.kind ? recommendedView.reason : currentView.description
	);
	const selectedObject = $derived($playback.selectedObject);
	const runDetails = $derived(runInspection(run));
	const fieldCellDetails = $derived(
		fieldCellInspection(
			selectedFrame,
			selectedObject?.kind === 'field-cell' ? selectedObject.id : null
		)
	);
	const graphNodeDetails = $derived(
		graphNodeInspection(
			selectedFrame,
			selectedObject?.kind === 'graph-node' ? selectedObject.id : null,
			events,
			pluginSemantics,
			selectionExplanation
		)
	);
	const graphEdgeDetails = $derived(
		graphEdgeInspection(
			selectedFrame,
			selectedObject?.kind === 'graph-edge' ? selectedObject.id : null,
			events,
			pluginSemantics
		)
	);
	const artifacts = $derived(artifactSummaries(run, metrics, events, $playback.frameBuffer));
	const entityBrowser = $derived(browseFrameEntities(selectedFrame, pluginSemantics));
	const metricDeck = $derived(
		buildMetricDeck({
			records: metrics,
			pluginSemantics,
			selectedTime: $playback.currentTime,
			pinnedMetrics: new Set(pinnedMetrics)
		})
	);
	const focusedMetric = $derived(
		metricDeck.find((item) => item.metric === focusedMetricId) ?? metricDeck[0] ?? null
	);
	const focusedMetricRecords = $derived(
		focusedMetric ? metrics.filter((record) => record.metric === focusedMetric.metric) : []
	);
	const recentEvents = $derived(
		[...events]
			.sort((left, right) => Number(right.t ?? -Infinity) - Number(left.t ?? -Infinity))
			.slice(0, 6)
	);
	const recentChangeItems = $derived(
		recentChangeCards({
			metrics,
			events,
			selectedTime: $playback.currentTime,
			explanation: frameExplanation ?? runExplanation
		})
	);
	const milestones = $derived(
		extractMilestones({
			metrics,
			events,
			frames: $playback.frameBuffer,
			explanation: runExplanation
		})
	);
	const explanationSections = $derived([
		{
			key: 'run',
			label: "What's happening",
			description: 'Run-level summary from deterministic facts and optional interpretation.',
			response: runExplanation,
			loading: runExplanationLoading
		},
		{
			key: 'frame',
			label: 'Current frame',
			description: selectedFrame
				? `${selectedFrame.frame_id} at ${formatTimeLabel(selectedFrame.t)}`
				: 'Pause playback or scrub to inspect a specific frame.',
			response: frameExplanation,
			loading: frameExplanationLoading
		},
		{
			key: 'selection',
			label: 'Selected entity',
			description: selectedObject
				? selectedObjectSummary()
				: 'Select a field cell or graph node to load targeted interpretation.',
			response: selectionExplanation,
			loading: selectionExplanationLoading
		}
	]);

	$effect(() => {
		const options = viewOptions;
		if (!options.length) return;
		const selectedStillAvailable = selectedView
			? options.some((view) => view.kind === selectedView)
			: false;
		if (!selectedViewLocked || !selectedStillAvailable) {
			selectedView = recommendedView.kind;
			activeDockTab = defaultDockTab(recommendedView.kind);
		}
	});

	$effect(() => {
		if (metricDeck.length === 0) {
			focusedMetricId = null;
			return;
		}
		if (!focusedMetricId || !metricDeck.some((item) => item.metric === focusedMetricId)) {
			focusedMetricId = metricDeck[0]?.metric ?? null;
		}
	});

	$effect(() => {
		const frameId = selectedFrame?.frame_id;
		if (!run || !frameId) {
			frameExplanation = null;
			loadedFrameExplanationKey = '';
			return;
		}
		if ($playback.status === 'playing') return;
		const key = `${run.run_id}:${frameId}`;
		const runId = run.run_id;
		if (loadedFrameExplanationKey === key) return;
		loadedFrameExplanationKey = key;
		frameExplanationLoading = true;
		void api
			.getFrameExplanation(runId, frameId)
			.then((response) => {
				if (loadedFrameExplanationKey === key) frameExplanation = response;
			})
			.catch(() => {
				if (loadedFrameExplanationKey === key)
					frameExplanation = unavailableExplanation(runId, 'frame');
			})
			.finally(() => {
				if (loadedFrameExplanationKey === key) frameExplanationLoading = false;
			});
	});

	$effect(() => {
		const selectionId = selectedObject?.id;
		if (!run || !selectionId) {
			selectionExplanation = null;
			loadedSelectionExplanationKey = '';
			return;
		}
		if ($playback.status === 'playing') return;
		const key = `${run.run_id}:${selectionId}`;
		const runId = run.run_id;
		if (loadedSelectionExplanationKey === key) return;
		loadedSelectionExplanationKey = key;
		selectionExplanationLoading = true;
		void api
			.getSelectionExplanation(runId, selectionId)
			.then((response) => {
				if (loadedSelectionExplanationKey === key) selectionExplanation = response;
			})
			.catch(() => {
				if (loadedSelectionExplanationKey === key) {
					selectionExplanation = unavailableExplanation(runId, 'selection');
				}
			})
			.finally(() => {
				if (loadedSelectionExplanationKey === key) selectionExplanationLoading = false;
			});
	});

	onMount(() => {
		let metricStream: EventSource | null = null;
		let refreshTimer: ReturnType<typeof setInterval> | null = null;
		void (async () => {
			try {
				const [runResult, metricResult, eventResult] = await Promise.all([
					api.getRun(data.runId),
					api.getMetrics(data.runId),
					api.getEvents(data.runId)
				]);
				run = runResult;
				metrics = metricResult;
				events = eventResult;
				try {
					fieldArtifacts = await api.listFields(data.runId);
				} catch {
					fieldArtifacts = [];
				}
				await loadRunExplanation(runResult.run_id);
				if (runResult.status === 'completed' || runResult.status === 'failed') {
					await playback.loadReplay(data.runId);
					playback.play();
				} else {
					playback.connectLive(data.runId);
					playback.play();
				}
				metricStream = openMetricStream();
				refreshTimer = setInterval(() => void refreshRun(), 1500);
			} catch (err) {
				error = err instanceof Error ? err.message : 'Unable to load run.';
			}
		})();

		return () => {
			metricStream?.close();
			playback.destroy();
			if (refreshTimer) clearInterval(refreshTimer);
		};
	});

	function openMetricStream(): EventSource {
		const stream = new EventSource(api.streamUrl(data.runId));
		streamState = 'connected';
		stream.addEventListener('metric', (event) => {
			const record = JSON.parse((event as MessageEvent).data) as MetricRecord;
			const key = metricKey(record);
			if (!metrics.some((existing) => metricKey(existing) === key)) {
				metrics = [...metrics, record].sort((left, right) => left.t - right.t);
			}
		});
		stream.onerror = () => {
			streamState = 'closed';
			stream.close();
			void refreshRun();
		};
		return stream;
	}

	async function refreshRun() {
		try {
			const previousStatus = run?.status;
			const nextRun = await api.getRun(data.runId);
			run = nextRun;
			if (!runExplanation || nextRun.status !== previousStatus) {
				await loadRunExplanation(nextRun.run_id);
			}
		} catch {
			// Existing data remains useful if a transient refresh fails.
		}
	}

	async function loadRunExplanation(runId: string) {
		runExplanationLoading = true;
		try {
			runExplanation = await api.getRunExplanation(runId);
		} catch {
			runExplanation = unavailableExplanation(runId, 'run');
		} finally {
			runExplanationLoading = false;
		}
	}

	function metricKey(record: MetricRecord): string {
		return `${record.t}:${record.metric}:${record.value}`;
	}

	function handleViewChange(value: string) {
		selectedView = value as StandardViewKind;
		selectedViewLocked = true;
		activeDockTab = defaultDockTab(selectedView);
	}

	function togglePlayback() {
		if ($playback.status === 'playing') {
			playback.pause();
		} else {
			playback.play();
		}
	}

	function handleRunKeydown(event: KeyboardEvent) {
		const target = event.target as HTMLElement | null;
		const action = shortcutActionFromEvent({
			key: event.key,
			code: event.code,
			ctrlKey: event.ctrlKey,
			metaKey: event.metaKey,
			altKey: event.altKey,
			targetTagName: target?.tagName ?? null,
			isContentEditable: target?.isContentEditable
		});
		if (!action) return;
		event.preventDefault();
		switch (action) {
			case 'toggle_playback':
				togglePlayback();
				return;
			case 'previous_frame':
				playback.pause();
				playback.stepFrame(-1);
				return;
			case 'next_frame':
				playback.pause();
				playback.stepFrame(1);
				return;
			case 'toggle_viewport_focus':
				focusSurface = toggleFocusSurface(focusSurface, 'viewport');
				return;
			case 'toggle_metric_focus':
				if (focusedMetric) focusSurface = toggleFocusSurface(focusSurface, 'metrics');
				return;
			case 'clear_focus':
				focusSurface = 'none';
		}
	}

	function defaultDockTab(view: StandardViewKind | null): string {
		if (!view) return 'metrics';
		const surface = standardViews.find((candidate) => candidate.kind === view)?.surface;
		if (surface === 'table') return 'frames';
		if (surface === 'metrics') return 'metrics';
		return 'metrics';
	}

	function toggleMetricPin(metric: string) {
		pinnedMetrics = [...togglePinnedMetric(new Set(pinnedMetrics), metric)];
	}

	function toggleMetricExpanded(metric: string) {
		expandedMetrics = expandedMetrics.includes(metric)
			? expandedMetrics.filter((candidate) => candidate !== metric)
			: [...expandedMetrics, metric];
	}

	function focusMetric(metric: string) {
		focusedMetricId = metric;
		activeDockTab = 'metrics';
	}

	function openMetricFullscreen(metric: string) {
		focusMetric(metric);
		focusSurface = 'metrics';
	}

	function toggleViewportFullscreen() {
		if (currentView.surface !== 'viewport') return;
		focusSurface = toggleFocusSurface(focusSurface, 'viewport');
	}

	function toggleMetricFullscreen() {
		if (!focusedMetric) return;
		focusSurface = toggleFocusSurface(focusSurface, 'metrics');
	}

	function selectedObjectSummary(): string {
		if (graphNodeDetails) {
			return `${graphNodeDetails.label} · ${graphNodeDetails.state} · degree ${graphNodeDetails.degree}`;
		}
		if (graphEdgeDetails) {
			return `${graphEdgeDetails.label} · ${graphEdgeDetails.kind}`;
		}
		if (fieldCellDetails) {
			return `${fieldCellDetails.field}[${fieldCellDetails.row}, ${fieldCellDetails.column}]`;
		}
		return selectedObject ? `${selectedObject.kind}:${selectedObject.id}` : 'Nothing selected';
	}

	function explanationSeverityClass(response: ExplanationResponse | null): string {
		const severity =
			response?.interpretation?.summary?.severity ?? response?.interpretation?.facts[0]?.severity;
		return severityBadgeClass(severity);
	}

	function severityBadgeClass(severity: string | undefined): string {
		switch (severity) {
			case 'critical':
				return 'border-red-300 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200';
			case 'warning':
				return 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200';
			case 'notice':
				return 'border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200';
			default:
				return 'border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-200';
		}
	}

	function explanationTitle(response: ExplanationResponse | null): string {
		return (
			response?.interpretation?.summary?.title ??
			response?.interpretation?.facts[0]?.title ??
			'No interpretation yet'
		);
	}

	function explanationBody(response: ExplanationResponse | null): string {
		return (
			response?.interpretation?.summary?.summary ??
			response?.interpretation?.facts[0]?.summary ??
			response?.reason ??
			'This plugin has not emitted explanation facts for this scope yet.'
		);
	}

	function explanationMode(response: ExplanationResponse | null): string {
		const mode = response?.interpretation?.mode_applied;
		if (!mode) return 'Unavailable';
		if (mode === 'rules_only') return 'Deterministic';
		if (mode === 'minimal_ai') return 'AI-assisted';
		return 'Off';
	}

	function evidenceRows(
		response: ExplanationResponse | null
	): Array<{ label: string; value: string }> {
		return (
			response?.interpretation?.summary?.evidence ??
			response?.interpretation?.facts[0]?.evidence ??
			[]
		)
			.slice(0, 4)
			.map((item) => ({
				label: humanizeIdentifier(item.label),
				value: item.value == null ? 'n/a' : formatUnknownValue(item.value, item.unit ?? null)
			}));
	}

	function unavailableExplanation(
		runId: string,
		scope: ExplanationResponse['scope']
	): ExplanationResponse {
		return {
			run_id: runId,
			scope,
			available: false,
			reason: 'Interpretation is unavailable for this scope right now.',
			interpretation: null
		};
	}

	function formatMetricValue(item: MetricDeckItem | null): string {
		if (!item) return '-';
		return formatDisplayMetricValue(item.current.value, item.unit);
	}

	function explanationFacts(response: ExplanationResponse | null) {
		return response?.interpretation?.facts ?? [];
	}

	function openMilestone(milestone: NarrativeMilestone) {
		const target = milestonePlaybackTarget(milestone, $playback.frameBuffer);
		playback.pause();
		playback.scrubTo(target.time);
		if (target.frameId) playback.selectFrame(target.frameId);
	}
</script>

<svelte:window onkeydown={handleRunKeydown} />

<div class="min-w-0 space-y-4">
	<header class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
		<div class="min-w-0">
			<p class="studio-eyebrow">Run analysis workspace</p>
			<h1 class="text-2xl font-semibold tracking-tight break-words">{data.runId}</h1>
			<p class="text-sm text-muted-foreground">
				Viewport, interpretation, metrics, and inspection stay visible together so the run can be
				read without hunting below the fold.
			</p>
		</div>
		<div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground lg:justify-end">
			<span class="rounded-full border px-2 py-1">Space play/pause</span>
			<span class="rounded-full border px-2 py-1">Left/right previous and next frame</span>
			<span class="rounded-full border px-2 py-1">F viewport full-screen</span>
			<span class="rounded-full border px-2 py-1">M metric full-screen</span>
		</div>
	</header>

	{#if error}
		<Alert.Alert variant="destructive">
			<AlertCircle size={16} />
			<Alert.AlertTitle>Run unavailable</Alert.AlertTitle>
			<Alert.AlertDescription>{error}</Alert.AlertDescription>
		</Alert.Alert>
	{/if}

	<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
		<StudioPanel title="Run status">
			<div class="flex items-end justify-between gap-3">
				<div>
					<p class="text-xs text-muted-foreground">Lifecycle</p>
					<div class="mt-2">
						{#if run}<StatusBadge status={run.status} />{:else}<span>Loading</span>{/if}
					</div>
				</div>
				<div class="text-right text-xs text-muted-foreground">
					<p>Metric stream {streamState}</p>
					<p>Frames {$playback.frameBuffer.length}</p>
				</div>
			</div>
		</StudioPanel>
		<StudioPanel title="Selected time">
			<p class="text-3xl font-semibold tracking-tight">
				{formatNumber($playback.currentTime)}
			</p>
			<p class="mt-2 text-xs text-muted-foreground">
				Frame {selectedFrame?.frame_id ?? 'none'} · {$playback.status}
			</p>
		</StudioPanel>
		<StudioPanel title="Active view">
			<p class="text-lg font-semibold">{currentView.label}</p>
			<p class="mt-2 text-xs text-muted-foreground">{currentViewSummary}</p>
		</StudioPanel>
		<StudioPanel title="Focused metric">
			<p class="text-lg font-semibold break-words">
				{focusedMetric?.label ?? humanizeIdentifier(summary.primaryMetric)}
			</p>
			<p class="mt-2 text-xs text-muted-foreground">
				{focusedMetric
					? formatMetricValue(focusedMetric)
					: `Peak ${formatNumber(summary.peakValue)}`}
			</p>
		</StudioPanel>
	</div>

	<div
		class="grid gap-4 xl:grid-cols-[minmax(15rem,17rem)_minmax(0,1fr)] 2xl:grid-cols-[minmax(15rem,17rem)_minmax(0,1.25fr)_minmax(18rem,22rem)]"
	>
		<div class="grid min-w-0 content-start gap-4">
			<StudioPanel title="Run status and playback controls">
				<div class="grid gap-4">
					<div class="grid gap-2 text-sm">
						<div class="flex items-center justify-between gap-2">
							<span class="text-muted-foreground">Status</span>
							{#if run}
								<StatusBadge status={run.status} />
							{:else}
								<span>Loading</span>
							{/if}
						</div>
						<div class="flex items-center justify-between gap-2">
							<span class="text-muted-foreground">Metrics</span>
							<span>{metrics.length}</span>
						</div>
						<div class="flex items-center justify-between gap-2">
							<span class="text-muted-foreground">Events</span>
							<span>{events.length}</span>
						</div>
						<div class="flex items-center justify-between gap-2">
							<span class="text-muted-foreground">Selected object</span>
							<span class="max-w-[11rem] truncate text-right">
								{selectedObject ? selectedObject.id : 'none'}
							</span>
						</div>
					</div>
					<div class="flex flex-wrap gap-2">
						<Button
							variant="outline"
							size="icon-sm"
							aria-label="Jump to start"
							onclick={() => playback.jumpToStart()}
						>
							<SkipBack size={15} />
						</Button>
						<Button
							variant="outline"
							size="icon-sm"
							aria-label={$playback.status === 'playing' ? 'Pause playback' : 'Play playback'}
							onclick={togglePlayback}
						>
							{#if $playback.status === 'playing'}
								<CirclePause size={15} />
							{:else}
								<CirclePlay size={15} />
							{/if}
						</Button>
						<Button
							variant="outline"
							size="icon-sm"
							aria-label="Previous frame"
							onclick={() => {
								playback.pause();
								playback.stepFrame(-1);
							}}
						>
							<SkipBack size={15} />
						</Button>
						<Button
							variant="outline"
							size="icon-sm"
							aria-label="Next frame"
							onclick={() => {
								playback.pause();
								playback.stepFrame(1);
							}}
						>
							<SkipForward size={15} />
						</Button>
						<Button
							variant="outline"
							size="icon-sm"
							aria-label="Jump to end"
							onclick={() => playback.jumpToEnd()}
						>
							<SkipForward size={15} />
						</Button>
						<Button
							variant="ghost"
							size="icon-sm"
							aria-label="Reset speed"
							onclick={() => playback.setSpeed(1)}
						>
							<Rewind size={15} />
						</Button>
					</div>
					<label class="grid gap-1 text-xs text-muted-foreground">
						Playback speed
						<input
							type="range"
							min="0.25"
							max="4"
							step="0.25"
							value={$playback.speed}
							oninput={(event) => playback.setSpeed(Number(event.currentTarget.value))}
						/>
					</label>
				</div>
			</StudioPanel>

			<StudioPanel title="Viewport and view switcher">
				<div class="grid gap-3 text-sm">
					<div>
						<p class="text-xs text-muted-foreground">Default selection</p>
						<p class="font-medium">{recommendedView.label}</p>
						<p class="mt-1 text-xs text-muted-foreground">{recommendedView.reason}</p>
					</div>
					<label class="grid gap-1 text-xs text-muted-foreground">
						Active standard view
						<select
							class="rounded-md border bg-background px-2 py-1 text-sm text-foreground"
							value={selectedView ?? recommendedView.kind}
							onchange={(event) => handleViewChange(event.currentTarget.value)}
						>
							{#each viewOptions as view (view.kind)}
								<option value={view.kind}>{view.label}</option>
							{/each}
						</select>
					</label>
					<p class="text-xs text-muted-foreground">{currentView.description}</p>
				</div>
			</StudioPanel>
		</div>

		<div class="grid min-w-0 content-start gap-4">
			<StudioPanel title="Viewport">
				<div class="mb-3 flex items-center justify-between gap-3">
					<div>
						<p class="text-sm font-medium">{currentView.label}</p>
						<p class="text-xs text-muted-foreground">
							Selection and playback persist while switching layouts or entering full-screen focus.
						</p>
					</div>
					{#if currentView.surface === 'viewport'}
						<Button variant="outline" size="sm" onclick={toggleViewportFullscreen}>
							{#if focusSurface === 'viewport'}
								<Minimize2 size={15} />
							{:else}
								<Maximize2 size={15} />
							{/if}
							<span class="ml-2"
								>{focusSurface === 'viewport' ? 'Exit full-screen' : 'Full-screen'}</span
							>
						</Button>
					{/if}
				</div>
				<div class="relative min-h-[26rem] overflow-hidden rounded-xl border bg-muted/30">
					{#if currentView.surface === 'viewport'}
						<SimulationViewport
							frame={selectedFrame}
							mode={$playback.mode}
							status={$playback.status}
							speed={$playback.speed}
							bufferedFrames={$playback.frameBuffer.length}
							selectedObject={$playback.selectedObject}
							viewKind={currentView.kind}
							viewLabel={currentView.label}
							onSelect={(object) => playback.selectObject(object)}
						/>
					{:else if currentView.surface === 'metrics'}
						<div class="h-full overflow-auto p-4">
							<MetricTimeline
								records={metrics}
								{events}
								frames={$playback.frameBuffer}
								selectedTime={$playback.currentTime}
								onSelectTime={(time) => {
									playback.pause();
									playback.scrubTo(time);
								}}
							/>
						</div>
					{:else}
						<div class="h-full overflow-auto p-4">
							{#if entityBrowser.mode === 'grouped'}
								<div class="grid gap-4">
									{#each entityBrowser.groups as group (group.id)}
										<div class="rounded-lg border bg-background/80 p-3">
											<p
												class="text-xs font-semibold tracking-wide text-muted-foreground uppercase"
											>
												{group.label}
											</p>
											<div class="mt-3 grid gap-2">
												{#each group.rows as row (row.id)}
													<button
														type="button"
														class="flex min-w-0 items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left hover:bg-muted/40"
														onclick={() => playback.selectObject({ kind: row.kind, id: row.id })}
													>
														<span class="min-w-0 font-medium break-words">{row.label}</span>
														<span class="shrink-0 text-xs text-muted-foreground">{row.value}</span>
													</button>
												{/each}
											</div>
										</div>
									{/each}
									{#if entityBrowser.relationshipRows.length}
										<div class="rounded-lg border bg-background/80 p-3">
											<p
												class="text-xs font-semibold tracking-wide text-muted-foreground uppercase"
											>
												Relationships
											</p>
											<div class="mt-3 grid gap-2">
												{#each entityBrowser.relationshipRows as row (row.id)}
													<button
														type="button"
														class="flex min-w-0 items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left hover:bg-muted/40"
														onclick={() => playback.selectObject({ kind: row.kind, id: row.id })}
													>
														<span class="min-w-0 font-medium break-words">{row.label}</span>
														<span class="shrink-0 text-xs text-muted-foreground">{row.value}</span>
													</button>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							{:else}
								<div class="grid gap-2">
									{#each entityBrowser.rows as row (row.id)}
										<button
											type="button"
											class="flex min-w-0 items-center justify-between gap-3 rounded-lg border bg-background/80 px-3 py-2 text-left hover:bg-muted/40"
											onclick={() => playback.selectObject({ kind: row.kind, id: row.id })}
										>
											<div class="min-w-0">
												<p class="font-medium break-words">{row.label}</p>
												{#if row.description}
													<p class="text-xs text-muted-foreground">{row.description}</p>
												{/if}
											</div>
											<span class="shrink-0 text-xs text-muted-foreground">{row.value}</span>
										</button>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</StudioPanel>

			<StudioPanel
				title={focusedMetric ? `${focusedMetric.label} analysis` : 'Metric analysis'}
				description="Focus one metric at a time with playback-aligned charting, event markers, and threshold context."
			>
				<div class="mb-3 flex flex-wrap items-center justify-between gap-3">
					<div class="min-w-0 text-xs text-muted-foreground">
						{#if focusedMetric}
							Current {formatMetricValue(focusedMetric)} · {focusedMetric.attention.replace(
								'_',
								' '
							)}
						{:else}
							Choose a metric from the deck to inspect it here.
						{/if}
					</div>
					<Button
						variant="outline"
						size="sm"
						onclick={toggleMetricFullscreen}
						disabled={!focusedMetric}
					>
						{#if focusSurface === 'metrics'}
							<Minimize2 size={15} />
						{:else}
							<Maximize2 size={15} />
						{/if}
						<span class="ml-2"
							>{focusSurface === 'metrics' ? 'Exit full-screen' : 'Full-screen'}</span
						>
					</Button>
				</div>
				<MetricTimeline
					records={focusedMetricRecords}
					{events}
					frames={$playback.frameBuffer}
					selectedTime={$playback.currentTime}
					showCards={false}
					thresholds={focusedMetric?.thresholds}
					onSelectTime={(time) => {
						playback.pause();
						playback.scrubTo(time);
					}}
				/>
			</StudioPanel>
		</div>

		<div class="grid min-w-0 content-start gap-4 xl:col-span-2 2xl:col-span-1">
			<StudioPanel title="What's happening explanation">
				<div class="grid gap-3">
					{#each explanationSections as section (section.key)}
						<div class="rounded-xl border p-3">
							<div class="flex flex-wrap items-start justify-between gap-3">
								<div class="min-w-0">
									<p class="text-sm font-semibold">{section.label}</p>
									<p class="mt-1 text-xs text-muted-foreground">{section.description}</p>
								</div>
								{#if section.response?.interpretation}
									<span
										class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${explanationSeverityClass(section.response)}`}
									>
										{explanationMode(section.response)}
									</span>
								{/if}
							</div>
							{#if section.loading}
								<p class="mt-3 text-sm text-muted-foreground">Loading interpretation…</p>
							{:else}
								<div class="mt-3 space-y-2">
									<p class="font-medium">{explanationTitle(section.response)}</p>
									<p class="text-sm text-muted-foreground">{explanationBody(section.response)}</p>
									{#if section.response?.interpretation}
										<div class="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
											<span class="rounded-full border px-2 py-0.5">
												Facts {section.response.interpretation.facts.length}
											</span>
											<span class="rounded-full border px-2 py-0.5">
												{section.response.interpretation.cached ? 'Cached' : 'Fresh'}
											</span>
										</div>
									{/if}
									{#if evidenceRows(section.response).length}
										<div class="grid gap-1 rounded-lg bg-muted/30 p-2 text-xs">
											{#each evidenceRows(section.response) as evidence (`${section.key}:${evidence.label}`)}
												<div class="flex items-center justify-between gap-3">
													<span class="text-muted-foreground">{evidence.label}</span>
													<span class="font-medium text-foreground">{evidence.value}</span>
												</div>
											{/each}
										</div>
									{/if}
									{#if explanationFacts(section.response).length > 1}
										<div class="grid gap-2">
											{#each explanationFacts(section.response).slice(0, 3) as fact (`${section.key}:${fact.title}:${fact.t}`)}
												<div class="rounded-lg border bg-background/70 p-2">
													<div class="flex items-center justify-between gap-2">
														<p class="text-xs font-medium">{fact.title}</p>
														<span
															class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${severityBadgeClass(fact.severity)}`}
														>
															{formatTimeLabel(fact.t)}
														</span>
													</div>
													<p class="mt-1 text-xs text-muted-foreground">{fact.summary}</p>
												</div>
											{/each}
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			</StudioPanel>

			<StudioPanel
				title="What changed recently"
				description="Recent deterministic deltas and clickable milestones stay tied to replay time."
			>
				<div class="grid gap-3">
					{#if recentChangeItems.length}
						{#each recentChangeItems as item (`change:${item.label}`)}
							<div class="rounded-xl border p-3">
								<div class="flex items-center justify-between gap-3">
									<p class="text-sm font-semibold">{item.label}</p>
									<span
										class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${severityBadgeClass(item.severity)}`}
									>
										{item.severity}
									</span>
								</div>
								<p class="mt-2 text-sm text-muted-foreground">{item.summary}</p>
							</div>
						{/each}
					{:else}
						<p class="text-sm text-muted-foreground">
							Pause playback or load more metrics to surface recent changes.
						</p>
					{/if}

					<div class="rounded-xl border p-3">
						<div class="flex flex-wrap items-center justify-between gap-3">
							<div class="min-w-0">
								<p class="text-sm font-semibold">Milestone timeline</p>
								<p class="mt-1 text-xs text-muted-foreground">
									Peaks, threshold crossings, anomalies, and event bursts can jump playback
									directly.
								</p>
							</div>
							<span class="rounded-full border px-2 py-0.5 text-[11px] font-medium">
								{milestones.length} markers
							</span>
						</div>
						{#if milestones.length}
							<div class="mt-3 grid gap-3 md:grid-cols-2">
								{#each milestones as milestone (milestone.id)}
									<button
										type="button"
										class="min-w-0 rounded-xl border bg-background/80 p-3 text-left hover:bg-muted/40"
										onclick={() => openMilestone(milestone)}
									>
										<div class="flex items-center justify-between gap-2">
											<span
												class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${severityBadgeClass(milestone.severity)}`}
											>
												{milestone.kind.replace('_', ' ')}
											</span>
											<span class="text-[11px] text-muted-foreground">
												{formatTimeLabel(milestone.t)}
											</span>
										</div>
										<p class="mt-2 font-medium">{milestone.title}</p>
										<p class="mt-1 text-xs text-muted-foreground">{milestone.summary}</p>
									</button>
								{/each}
							</div>
						{:else}
							<p class="mt-3 text-sm text-muted-foreground">
								No milestones have been extracted from the current replay yet.
							</p>
						{/if}
					</div>
				</div>
			</StudioPanel>

			<StudioPanel
				title="Key metrics"
				description="Headline metrics, pinned metrics, and attention-ranked signals stay beside the viewport."
			>
				<MetricDeck
					items={metricDeck}
					focusedMetric={focusedMetric?.metric ?? null}
					{expandedMetrics}
					onFocusMetric={focusMetric}
					onToggleExpanded={toggleMetricExpanded}
					onTogglePin={toggleMetricPin}
					onOpenFullscreen={openMetricFullscreen}
				/>
			</StudioPanel>

			<StudioPanel title="Entity inspector">
				<div class="grid gap-3 text-sm">
					<div class="grid gap-1">
						<p class="text-xs text-muted-foreground">Selected frame</p>
						<p class="font-mono text-xs break-all">{selectedFrame?.frame_id ?? 'none'}</p>
					</div>
					<div class="grid gap-1">
						<p class="text-xs text-muted-foreground">Kind</p>
						<p>{selectedFrame?.kind ?? '-'}</p>
					</div>
					<div class="grid gap-1">
						<p class="text-xs text-muted-foreground">Selected object</p>
						<p class="font-mono text-xs break-all">
							{selectedObject ? `${selectedObject.kind}:${selectedObject.id}` : 'none'}
						</p>
					</div>
					{#if fieldCellDetails}
						<div class="rounded-lg border p-3">
							<p class="studio-eyebrow">Field cell</p>
							<p class="mt-2 font-mono text-xs">{fieldCellDetails.label}</p>
							<p class="text-sm">
								{fieldCellDetails.value ?? '-'}
								{fieldCellDetails.units}
							</p>
							<p class="mt-1 text-xs text-muted-foreground">
								{fieldCellDetails.dtype} · {fieldCellDetails.shape.join('x')} · {fieldCellDetails.source}
							</p>
						</div>
					{/if}
					{#if graphNodeDetails}
						<div class="grid gap-3 rounded-lg border p-3">
							<p class="studio-eyebrow">Graph node</p>
							<div>
								<p class="font-medium">{graphNodeDetails.label}</p>
								<p class="mt-1 text-xs text-muted-foreground">
									{graphNodeDetails.state} · degree {graphNodeDetails.degree}
									{#if graphNodeDetails.group}
										· {graphNodeDetails.group}
									{/if}
								</p>
							</div>
							{#if graphNodeDetails.metrics.length}
								<div class="grid gap-1 rounded-lg bg-muted/30 p-2 text-xs">
									{#each graphNodeDetails.metrics as metric (`metric:${metric.label}`)}
										<div class="flex items-center justify-between gap-3">
											<span class="text-muted-foreground">{metric.label}</span>
											<span class="font-medium">{metric.value}</span>
										</div>
									{/each}
								</div>
							{/if}
							{#if graphNodeDetails.fields.length}
								<div class="grid gap-1 rounded-lg bg-muted/30 p-2 text-xs">
									{#each graphNodeDetails.fields as field (`field:${field.label}`)}
										<div class="flex items-center justify-between gap-3">
											<span class="text-muted-foreground">{field.label}</span>
											<span class="font-medium">{field.value}</span>
										</div>
									{/each}
								</div>
							{/if}
							{#if graphNodeDetails.events.length}
								<div class="grid gap-2">
									<p class="text-xs font-medium text-muted-foreground">Recent events</p>
									{#each graphNodeDetails.events.slice(0, 3) as event, index (`node-event:${index}`)}
										<div class="rounded-lg border bg-background/70 p-2 text-xs">
											<p class="font-medium">
												{event.event_type ?? event.event ?? event.type ?? 'event'}
											</p>
											<p class="mt-1 text-muted-foreground">
												{formatTimeLabel(typeof event.t === 'number' ? event.t : null)}
											</p>
										</div>
									{/each}
								</div>
							{/if}
							{#if graphNodeDetails.facts.length}
								<div class="grid gap-2">
									<p class="text-xs font-medium text-muted-foreground">Selection facts</p>
									{#each graphNodeDetails.facts as fact (`fact:${fact.title}:${fact.t}`)}
										<div class="rounded-lg border bg-background/70 p-2 text-xs">
											<div class="flex items-center justify-between gap-2">
												<p class="font-medium">{fact.title}</p>
												<span
													class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${severityBadgeClass(fact.severity)}`}
												>
													{fact.severity}
												</span>
											</div>
											<p class="mt-1 text-muted-foreground">{fact.summary}</p>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
					{#if graphEdgeDetails}
						<div class="grid gap-3 rounded-lg border p-3">
							<p class="studio-eyebrow">Relationship</p>
							<div>
								<p class="font-medium">{graphEdgeDetails.label}</p>
								<p class="mt-1 text-xs text-muted-foreground">
									{graphEdgeDetails.kind}
									{#if graphEdgeDetails.weight !== null}
										· weight {formatNumber(graphEdgeDetails.weight)}
									{/if}
									· {graphEdgeDetails.directed ? 'directed' : 'undirected'}
								</p>
							</div>
							{#if graphEdgeDetails.fields.length}
								<div class="grid gap-1 rounded-lg bg-muted/30 p-2 text-xs">
									{#each graphEdgeDetails.fields as field (`edge-field:${field.label}`)}
										<div class="flex items-center justify-between gap-3">
											<span class="text-muted-foreground">{field.label}</span>
											<span class="font-medium">{field.value}</span>
										</div>
									{/each}
								</div>
							{/if}
							{#if graphEdgeDetails.events.length}
								<div class="grid gap-2">
									<p class="text-xs font-medium text-muted-foreground">Recent events</p>
									{#each graphEdgeDetails.events.slice(0, 3) as event, index (`edge-event:${index}`)}
										<div class="rounded-lg border bg-background/70 p-2 text-xs">
											<p class="font-medium">
												{event.event_type ?? event.event ?? event.type ?? 'event'}
											</p>
											<p class="mt-1 text-muted-foreground">
												{formatTimeLabel(typeof event.t === 'number' ? event.t : null)}
											</p>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
					{#if runDetails}
						<details class="rounded-lg border p-3">
							<summary class="cursor-pointer text-sm font-medium">Technical details</summary>
							<div class="mt-3 grid gap-2 text-xs">
								<p><span class="text-muted-foreground">Run</span> {runDetails.runId}</p>
								<p><span class="text-muted-foreground">Status</span> {runDetails.status}</p>
								<p><span class="text-muted-foreground">Plugins</span> {runDetails.plugins}</p>
								<p>
									<span class="text-muted-foreground">Plugin versions</span>
									{runDetails.pluginVersions}
								</p>
								<p>
									<span class="text-muted-foreground">Runtime backend</span>
									{runDetails.runtimeBackend}
								</p>
								<p><span class="text-muted-foreground">Config</span> {runDetails.configHash}</p>
								<p><span class="text-muted-foreground">Seed plan</span> {runDetails.seedPlan}</p>
								<p>
									<span class="text-muted-foreground">Artifacts</span>
									{runDetails.artifactPath}
								</p>
							</div>
						</details>
					{/if}
				</div>
			</StudioPanel>
		</div>
	</div>

	<div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(18rem,22rem)]">
		<StudioPanel title="Events">
			<div class="grid gap-3">
				{#if recentEvents.length}
					{#each recentEvents as event, index (`recent:${index}`)}
						<div class="rounded-lg border p-3">
							<div class="flex items-center justify-between gap-3">
								<p class="font-medium">
									{event.event_type ?? event.event ?? event.type ?? 'event'}
								</p>
								<span class="text-xs text-muted-foreground">
									{formatTimeLabel(typeof event.t === 'number' ? event.t : null)}
								</span>
							</div>
							<p class="mt-2 truncate font-mono text-xs text-muted-foreground">
								{JSON.stringify(event)}
							</p>
						</div>
					{/each}
				{:else}
					<p class="text-sm text-muted-foreground">No events have been emitted yet.</p>
				{/if}
			</div>
		</StudioPanel>

		<StudioPanel title="Artifacts">
			<div class="grid gap-3 text-sm">
				<div class="grid gap-2">
					<!-- eslint-disable svelte/no-navigation-without-resolve -->
					<a class="studio-action-link" href={api.exportRunUrl(data.runId, 'csv')}>CSV export</a>
					<a class="studio-action-link" href={api.exportRunUrl(data.runId, 'parquet')}>
						Parquet export
					</a>
					<!-- eslint-enable svelte/no-navigation-without-resolve -->
					<a class="studio-action-link" href={resolve(`/compare?runA=${data.runId}`)}>
						Compare this run
					</a>
				</div>
				<div class="grid gap-2">
					{#each artifacts as artifact (artifact.kind)}
						<div class="flex items-center justify-between gap-3 rounded-lg border p-2">
							<div>
								<p class="font-medium">{artifact.label}</p>
								<p class="text-xs text-muted-foreground">{artifact.count} available</p>
							</div>
							<!-- eslint-disable svelte/no-navigation-without-resolve -->
							<a class="text-sm font-medium text-primary hover:underline" href={artifact.href}
								>Open</a
							>
							<!-- eslint-enable svelte/no-navigation-without-resolve -->
						</div>
					{/each}
				</div>
			</div>
		</StudioPanel>
	</div>

	<StudioPanel title="Detailed analysis">
		<Tabs.Tabs bind:value={activeDockTab} class="space-y-4">
			<Tabs.TabsList>
				<Tabs.TabsTrigger value="metrics">Metrics</Tabs.TabsTrigger>
				<Tabs.TabsTrigger value="events">Events</Tabs.TabsTrigger>
				<Tabs.TabsTrigger value="frames">Frames</Tabs.TabsTrigger>
				<Tabs.TabsTrigger value="artifacts">Artifacts</Tabs.TabsTrigger>
				<Tabs.TabsTrigger value="logs">Logs</Tabs.TabsTrigger>
				<Tabs.TabsTrigger value="manifest">Manifest</Tabs.TabsTrigger>
			</Tabs.TabsList>

			<Tabs.TabsContent value="metrics">
				<div class="mb-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
					<StudioPanel title="Selected time">
						<p class="text-2xl font-semibold">{formatNumber($playback.currentTime)}</p>
					</StudioPanel>
					<StudioPanel title="Current frame">
						<p class="truncate text-2xl font-semibold">{selectedFrame?.frame_id ?? '-'}</p>
					</StudioPanel>
					<StudioPanel title="Peak value">
						<p class="text-2xl font-semibold">{formatNumber(summary.peakValue)}</p>
					</StudioPanel>
					<StudioPanel title="Final value">
						<p class="text-2xl font-semibold">{formatNumber(summary.finalValue)}</p>
					</StudioPanel>
					<StudioPanel title="Elapsed time">
						<p class="text-2xl font-semibold">{formatNumber(summary.duration)}</p>
					</StudioPanel>
				</div>
				<MetricTimeline
					records={metrics}
					{events}
					frames={$playback.frameBuffer}
					selectedTime={$playback.currentTime}
					onSelectTime={(time) => {
						playback.pause();
						playback.scrubTo(time);
					}}
				/>
			</Tabs.TabsContent>

			<Tabs.TabsContent value="events">
				<Table.Table>
					<Table.TableHeader>
						<Table.TableRow>
							<Table.TableHead>t</Table.TableHead>
							<Table.TableHead>event</Table.TableHead>
							<Table.TableHead>payload</Table.TableHead>
						</Table.TableRow>
					</Table.TableHeader>
					<Table.TableBody>
						{#each events as event, index (index)}
							<Table.TableRow>
								<Table.TableCell>
									{typeof event.t === 'number' ? formatNumber(event.t) : '-'}
								</Table.TableCell>
								<Table.TableCell>{event.event_type ?? event.type ?? '-'}</Table.TableCell>
								<Table.TableCell class="font-mono text-xs">{JSON.stringify(event)}</Table.TableCell>
							</Table.TableRow>
						{/each}
					</Table.TableBody>
				</Table.Table>
			</Tabs.TabsContent>

			<Tabs.TabsContent value="frames">
				<Table.Table>
					<Table.TableHeader>
						<Table.TableRow>
							<Table.TableHead>frame</Table.TableHead>
							<Table.TableHead>kind</Table.TableHead>
							<Table.TableHead>t</Table.TableHead>
						</Table.TableRow>
					</Table.TableHeader>
					<Table.TableBody>
						{#each $playback.frameBuffer as frame (frame.frame_id)}
							<Table.TableRow>
								<Table.TableCell class="font-mono text-xs">{frame.frame_id}</Table.TableCell>
								<Table.TableCell>{frame.kind}</Table.TableCell>
								<Table.TableCell>{formatNumber(frame.t)}</Table.TableCell>
							</Table.TableRow>
						{/each}
					</Table.TableBody>
				</Table.Table>
			</Tabs.TabsContent>

			<Tabs.TabsContent value="artifacts">
				<div class="mb-3 flex flex-wrap gap-2">
					<!-- eslint-disable svelte/no-navigation-without-resolve -->
					<a class="studio-action-link" href={api.exportRunUrl(data.runId, 'csv')}>CSV export</a>
					<a class="studio-action-link" href={api.exportRunUrl(data.runId, 'parquet')}>
						Parquet export
					</a>
					<!-- eslint-enable svelte/no-navigation-without-resolve -->
					<a class="studio-action-link" href={resolve(`/compare?runA=${data.runId}`)}>
						Compare this run
					</a>
					{#if selectedFrame}
						<!-- eslint-disable svelte/no-navigation-without-resolve -->
						<a class="studio-action-link" href={api.frameUrl(data.runId, selectedFrame.frame_id)}>
							Frame payload
						</a>
						<!-- eslint-enable svelte/no-navigation-without-resolve -->
					{/if}
				</div>
				<Table.Table>
					<Table.TableHeader>
						<Table.TableRow>
							<Table.TableHead>artifact</Table.TableHead>
							<Table.TableHead>count</Table.TableHead>
							<Table.TableHead>open</Table.TableHead>
						</Table.TableRow>
					</Table.TableHeader>
					<Table.TableBody>
						{#each artifacts as artifact (artifact.kind)}
							<Table.TableRow>
								<Table.TableCell>{artifact.label}</Table.TableCell>
								<Table.TableCell>{artifact.count}</Table.TableCell>
								<Table.TableCell>
									<!-- eslint-disable svelte/no-navigation-without-resolve -->
									<a class="font-medium text-primary hover:underline" href={artifact.href}>Open</a>
									<!-- eslint-enable svelte/no-navigation-without-resolve -->
								</Table.TableCell>
							</Table.TableRow>
						{/each}
						{#each fieldArtifacts as field, index (field.field_id ?? field.id ?? index)}
							<Table.TableRow>
								<Table.TableCell
									>{field.name ?? field.field_id ?? field.id ?? 'field'}</Table.TableCell
								>
								<Table.TableCell
									>{Array.isArray(field.shape) ? field.shape.join('x') : '-'}</Table.TableCell
								>
								<Table.TableCell>
									<!-- eslint-disable svelte/no-navigation-without-resolve -->
									<a
										class="font-medium text-primary hover:underline"
										href={api.fieldUrl(
											data.runId,
											String(field.field_id ?? field.id ?? field.name ?? index),
											'csv'
										)}
									>
										CSV
									</a>
									<!-- eslint-enable svelte/no-navigation-without-resolve -->
								</Table.TableCell>
							</Table.TableRow>
						{/each}
					</Table.TableBody>
				</Table.Table>
			</Tabs.TabsContent>

			<Tabs.TabsContent value="logs">
				<Table.Table>
					<Table.TableHeader>
						<Table.TableRow>
							<Table.TableHead>source</Table.TableHead>
							<Table.TableHead>status</Table.TableHead>
							<Table.TableHead>detail</Table.TableHead>
						</Table.TableRow>
					</Table.TableHeader>
					<Table.TableBody>
						<Table.TableRow>
							<Table.TableCell>frame stream</Table.TableCell>
							<Table.TableCell>{$playback.status}</Table.TableCell>
							<Table.TableCell class="font-mono text-xs">
								{$playback.error ?? `${$playback.frameBuffer.length} buffered frames`}
							</Table.TableCell>
						</Table.TableRow>
						<Table.TableRow>
							<Table.TableCell>metric stream</Table.TableCell>
							<Table.TableCell>{streamState}</Table.TableCell>
							<Table.TableCell class="font-mono text-xs"
								>{metrics.length} metric records</Table.TableCell
							>
						</Table.TableRow>
					</Table.TableBody>
				</Table.Table>
			</Tabs.TabsContent>

			<Tabs.TabsContent value="manifest">
				<pre class="overflow-auto rounded-md bg-muted p-4 text-xs">{JSON.stringify(
						run,
						null,
						2
					)}</pre>
			</Tabs.TabsContent>
		</Tabs.Tabs>
	</StudioPanel>
</div>

{#if focusSurface === 'viewport' && currentView.surface === 'viewport'}
	<div class="fixed inset-0 z-50 bg-background/85 p-4 backdrop-blur-sm">
		<div class="flex h-full flex-col gap-4 rounded-2xl border bg-background p-4 shadow-2xl">
			<div class="flex items-center justify-between gap-3">
				<div>
					<p class="text-sm font-semibold">{currentView.label} full-screen</p>
					<p class="text-xs text-muted-foreground">
						Playback and selection remain live while this overlay is open.
					</p>
				</div>
				<Button variant="outline" size="sm" onclick={() => (focusSurface = 'none')}>
					<Minimize2 size={15} />
					<span class="ml-2">Close</span>
				</Button>
			</div>
			<div class="relative min-h-0 flex-1 overflow-hidden rounded-xl border bg-muted/30">
				<SimulationViewport
					frame={selectedFrame}
					mode={$playback.mode}
					status={$playback.status}
					speed={$playback.speed}
					bufferedFrames={$playback.frameBuffer.length}
					selectedObject={$playback.selectedObject}
					viewKind={currentView.kind}
					viewLabel={currentView.label}
					onSelect={(object) => playback.selectObject(object)}
				/>
			</div>
		</div>
	</div>
{/if}

{#if focusSurface === 'metrics' && focusedMetric}
	<div class="fixed inset-0 z-50 bg-background/85 p-4 backdrop-blur-sm">
		<div class="flex h-full flex-col gap-4 rounded-2xl border bg-background p-4 shadow-2xl">
			<div class="flex items-center justify-between gap-3">
				<div>
					<p class="text-sm font-semibold">{focusedMetric.label} full-screen analysis</p>
					<p class="text-xs text-muted-foreground">
						Focused metric view keeps threshold markers, events, and frame scrubbing in one place.
					</p>
				</div>
				<Button variant="outline" size="sm" onclick={() => (focusSurface = 'none')}>
					<Minimize2 size={15} />
					<span class="ml-2">Close</span>
				</Button>
			</div>
			<div class="min-h-0 flex-1 overflow-auto rounded-xl border p-4">
				<MetricTimeline
					records={focusedMetricRecords}
					{events}
					frames={$playback.frameBuffer}
					selectedTime={$playback.currentTime}
					showCards={false}
					thresholds={focusedMetric.thresholds}
					onSelectTime={(time) => {
						playback.pause();
						playback.scrubTo(time);
					}}
				/>
			</div>
		</div>
	</div>
{/if}
