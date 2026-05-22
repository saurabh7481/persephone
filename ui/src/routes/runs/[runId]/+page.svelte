<script lang="ts">
	import { resolve } from '$app/paths';
	import { onMount, tick } from 'svelte';
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
	import { MetricDeck, RunSummaryHero, RunSecondaryTabs, SimulationViewport, StudioPanel } from '$lib/components/studio';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Table from '$lib/components/ui/table';
	import * as Tabs from '$lib/components/ui/tabs';
	import { createPlaybackStore, playbackSourceFromApi } from '$lib/studio/playback';
	import {
		artifactSummaries,
		buildInspectorPanelModel,
		browseFrameEntities,
		fieldCellInspection,
		graphEdgeInspection,
		graphNodeInspection,
		inspectorPreview,
		runInspection
	} from '$lib/studio/inspector';
	import { buildMetricDeck, togglePinnedMetric, type MetricDeckItem } from '$lib/studio/metrics';
	import {
		buildExplanationPanelCards,
		buildNarrativeLead,
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
	import { buildRunPageModel } from '$lib/studio/run-page';
	import {
		formatMetricValue as formatDisplayMetricValue,
		formatNumber,
		formatTimeLabel,
		humanizeIdentifier
	} from '$lib/studio/format';
	import {
		availableViews,
		chooseDefaultView,
		standardViews,
		viewNarrative,
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
	let activeSecondaryTab = $state('artifacts');
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
	let viewportDialogCloseButton = $state<HTMLButtonElement | null>(null);
	let metricDialogCloseButton = $state<HTMLButtonElement | null>(null);

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
	const currentViewNarrative = $derived(
		viewNarrative({
			current: currentView,
			recommended: recommendedView,
			locked: selectedViewLocked
		})
	);
	const selectedObject = $derived($playback.selectedObject);
	const runDetails = $derived(runInspection(run));
	const fieldCellDetails = $derived(
		fieldCellInspection(
			selectedFrame,
			selectedObject?.kind === 'field-cell' ? selectedObject.id : null,
			selectionExplanation
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
			pluginSemantics,
			selectionExplanation
		)
	);
	const inspectorPanel = $derived(
		buildInspectorPanelModel({
			selectedFrame,
			fieldCell: fieldCellDetails,
			graphNode: graphNodeDetails,
			graphEdge: graphEdgeDetails,
			run: runDetails
		})
	);
	const inspectorPreviewModel = $derived(inspectorPreview(inspectorPanel));
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
	const narrativeLead = $derived(
		buildNarrativeLead({
			explanation: frameExplanation ?? runExplanation,
			recentChanges: recentChangeItems,
			viewLabel: currentView.label,
			viewPurpose: currentView.purpose
		})
	);
	const keyMetrics = $derived(
		metricDeck.filter((item) => item.pinned || item.headline).length
			? [
					...metricDeck.filter((item) => item.pinned || item.headline),
					...metricDeck.filter((item) => !item.pinned && !item.headline)
				].slice(0, Math.min(6, metricDeck.length))
			: metricDeck.slice(0, Math.min(6, metricDeck.length))
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
	const explanationCards = $derived(buildExplanationPanelCards(explanationSections));
	const pageModel = $derived(
		buildRunPageModel({
			runStatus: run?.status ?? 'loading',
			currentView,
			narrativeLead,
			focusedMetric,
			explanationCards,
			recentChanges: recentChangeItems,
			inspectorKind: inspectorPanel.kind,
			hasSelection: selectedObject !== null,
			pluginSupportsExplanation: pluginSemantics.some(
				(s) => (s.semantics.explanation_capabilities ?? []).length > 0
			),
			currentFrameId: selectedFrame?.frame_id ?? null
		})
	);

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
		if (focusSurface === 'viewport') {
			void tick().then(() => viewportDialogCloseButton?.focus());
		}
		if (focusSurface === 'metrics') {
			void tick().then(() => metricDialogCloseButton?.focus());
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

	function openMilestone(milestone: NarrativeMilestone) {
		const target = milestonePlaybackTarget(milestone, $playback.frameBuffer);
		playback.pause();
		playback.scrubTo(target.time);
		if (target.frameId) playback.selectFrame(target.frameId);
	}

	function secondaryTabLabel(value: string): string {
		const labels: Record<string, string> = {
			explain: 'Explain',
			inspect: 'Inspect',
			timeline: 'Timeline',
			artifacts: 'Artifacts',
			debug: 'Debug'
		};
		return labels[value] ?? value;
	}

	function openExplanationMoment(time: number) {
		const frame = $playback.frameBuffer.reduce<import('$lib/api-client').SimulationFrame | null>(
			(nearest, candidate) => {
				if (!nearest) return candidate;
				return Math.abs(candidate.t - time) < Math.abs(nearest.t - time) ? candidate : nearest;
			},
			null
		);
		playback.pause();
		playback.scrubTo(frame?.t ?? time);
		if (frame?.frame_id) playback.selectFrame(frame.frame_id);
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

	<div class="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(20rem,0.95fr)]">
		<StudioPanel title={narrativeLead.eyebrow}>
			<RunSummaryHero
				status={run?.status ?? 'loading'}
				viewLabel={currentView.label}
				title={pageModel.summary.title}
				summary={pageModel.summary.summary}
				significance={pageModel.summary.significance}
				nextStep={pageModel.summary.nextStep}
				currentFrame={pageModel.summary.currentFrame}
				metricLabel={focusedMetric?.label ?? 'No primary metric'}
				metricValue={focusedMetric ? formatMetricValue(focusedMetric) : '-'}
			/>
		</StudioPanel>

		<StudioPanel title="View guide" description={currentViewNarrative.summary}>
			<div class="grid gap-3 text-sm">
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
				<div class="rounded-xl border bg-muted/25 p-3">
					<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
						Best when
					</p>
					<p class="mt-2 leading-6">{currentView.bestFit}</p>
				</div>
				<div class="rounded-xl border bg-muted/25 p-3">
					<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
						Fallback
					</p>
					<p class="mt-2 leading-6">{currentView.fallback}</p>
				</div>
				<p class="text-xs leading-5 text-muted-foreground">{currentViewNarrative.nextStep}</p>
			</div>
		</StudioPanel>
	</div>

	<StudioPanel
		title="Key metrics"
		description="Showing the highest-priority metrics first so the run story stays visible before deeper inspection."
	>
		<div
			class="mb-3 flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground"
		>
			<p>
				Top headline, pinned, and attention-ranked metrics stay grouped beside the main narrative.
			</p>
			<p>
				Showing {keyMetrics.length} of {metricDeck.length}
			</p>
		</div>
		<MetricDeck
			items={keyMetrics}
			focusedMetric={focusedMetric?.metric ?? null}
			{expandedMetrics}
			onFocusMetric={focusMetric}
			onToggleExpanded={toggleMetricExpanded}
			onTogglePin={toggleMetricPin}
			onOpenFullscreen={openMetricFullscreen}
		/>
	</StudioPanel>

	<div
		class="grid gap-4 xl:grid-cols-[minmax(15rem,17rem)_minmax(0,1fr)]"
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

			<StudioPanel title="Playback and view controls">
				<div class="grid gap-3 text-sm">
					<div>
						<p class="text-xs text-muted-foreground">Why this view is showing now</p>
						<p class="font-medium">{currentViewNarrative.title}</p>
						<p class="mt-1 text-xs text-muted-foreground">{recommendedView.reason}</p>
					</div>
					<div class="rounded-xl border bg-muted/25 p-3">
						<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
							View help
						</p>
						<p class="mt-2 text-xs leading-5 text-muted-foreground">{currentView.help}</p>
					</div>
				</div>
			</StudioPanel>
		</div>

		<div class="grid min-w-0 content-start gap-4">
			<StudioPanel title="Viewport">
				<div class="mb-3 flex items-center justify-between gap-3">
					<div class="min-w-0">
						<p class="text-sm font-medium">{currentView.label}</p>
						<p class="mt-1 text-xs text-muted-foreground">{currentView.purpose}</p>
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
							viewPurpose={currentView.purpose}
							viewHelp={currentView.help}
							loadingTitle={currentView.loading.title}
							loadingBody={currentView.loading.body}
							emptyTitle={currentView.empty.title}
							emptyBody={currentView.empty.body}
							onSelect={(object) => playback.selectObject(object)}
						/>
					{:else if currentView.surface === 'metrics'}
						<div class="h-full overflow-auto p-4">
							<div class="mb-4 rounded-xl border bg-background/80 p-3">
								<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
									Why this view fits
								</p>
								<p class="mt-2 text-sm leading-6">{currentView.bestFit}</p>
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
						</div>
					{:else}
						<div class="h-full overflow-auto p-4">
							<div class="mb-4 grid gap-3 lg:grid-cols-2">
								<div class="rounded-xl border bg-background/80 p-3">
									<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
										Best when
									</p>
									<p class="mt-2 text-sm leading-6">{currentView.bestFit}</p>
								</div>
								<div class="rounded-xl border bg-background/80 p-3">
									<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
										Selection
									</p>
									<p class="mt-2 text-sm leading-6">{currentView.help}</p>
								</div>
							</div>
							{#if entityBrowser.mode === 'grouped' && entityBrowser.groups.length}
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
							{:else if entityBrowser.mode === 'table' && entityBrowser.rows.length}
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
							{:else}
								<div class="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
									<p class="font-medium text-foreground">{currentView.empty.title}</p>
									<p class="mt-2 leading-6">{currentView.empty.body}</p>
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

	</div>

	<StudioPanel title="Details">
		<RunSecondaryTabs
			tabs={pageModel.secondaryTabs.map((value) => ({ value, label: secondaryTabLabel(value) }))}
			bind:activeTab={activeSecondaryTab}
		>
			{#snippet children(tabValue)}
				{#if tabValue === 'explain'}
					<div class="grid gap-3">
						{#each explanationCards as card (card.key)}
							<div class="rounded-2xl border bg-background/90 p-4 shadow-sm">
								<div class="flex items-center justify-between gap-3">
									<p class="text-sm font-semibold">{card.sourceLabel}</p>
								</div>
								<p class="mt-3 text-sm leading-6">{card.primaryStatement}</p>
								{#if card.supportingDetail}
									<p class="mt-2 text-xs leading-5 text-muted-foreground">{card.supportingDetail}</p>
								{/if}
								{#if card.evidence?.length}
									<div class="mt-3 flex flex-wrap gap-2">
										{#each card.evidence as ev (`evidence:${ev.label}`)}
											<span class="inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
												{ev.label}: {ev.value}
											</span>
										{/each}
									</div>
								{/if}
								{#if card.facts?.length}
									<div class="mt-3 grid gap-2">
										{#each card.facts as fact (`fact:${fact.title}`)}
											<button
												type="button"
												class="rounded-xl border bg-muted/15 p-3 text-left hover:bg-muted/25"
												onclick={() => openExplanationMoment(fact.time ?? 0)}
											>
												<p class="text-xs font-semibold">{fact.title}</p>
												<p class="mt-1 text-xs leading-5 text-muted-foreground">{fact.summary}</p>
											</button>
										{/each}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else if tabValue === 'inspect'}
					<div class="grid gap-4 text-sm">
						<div class="rounded-2xl border bg-background/90 p-4 shadow-sm">
							<p class="studio-eyebrow">{inspectorPanel.eyebrow}</p>
							<h3 class="mt-2 text-lg font-semibold">{inspectorPanel.title}</h3>
							<p class="mt-2 text-sm leading-6 text-muted-foreground">{inspectorPanel.summary}</p>
						</div>

						{#if inspectorPanel.highlights.length}
							<div class="grid gap-3 sm:grid-cols-2">
								{#each inspectorPanel.highlights as item (`inspector-highlight:${item.label}`)}
									<div class="rounded-xl border bg-muted/20 p-3">
										<p class="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
											{item.label}
										</p>
										<p class="mt-2 text-sm font-medium break-words">{item.value}</p>
										{#if item.description}
											<p class="mt-1 text-xs leading-5 text-muted-foreground">{item.description}</p>
										{/if}
									</div>
								{/each}
							</div>
						{/if}

						{#if inspectorPanel.sections.length}
							<div class="grid gap-3">
								{#each inspectorPanel.sections as section (`inspector-section:${section.title}`)}
									<div class="rounded-2xl border bg-background/90 p-4 shadow-sm">
										<p class="text-sm font-semibold">{section.title}</p>
										{#if section.description}
											<p class="mt-1 text-xs leading-5 text-muted-foreground">{section.description}</p>
										{/if}
										<div class="mt-3 grid gap-2">
											{#each section.items as item (`${section.title}:${item.label}:${item.value}`)}
												<div class="rounded-xl border bg-muted/15 p-3">
													<div class="flex items-start justify-between gap-3">
														<p class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
															{item.label}
														</p>
														<p class="text-right text-sm font-medium break-words">{item.value}</p>
													</div>
													{#if item.description}
														<p class="mt-2 text-xs leading-5 text-muted-foreground">{item.description}</p>
													{/if}
												</div>
											{/each}
										</div>
									</div>
								{/each}
							</div>
						{:else if inspectorPanel.kind !== 'empty'}
							<p class="text-sm text-muted-foreground">
								This selection does not have additional local metrics or related events yet.
							</p>
						{/if}

						<details class="rounded-2xl border bg-background/90 p-4 shadow-sm">
							<summary class="cursor-pointer text-sm font-medium">Technical details</summary>
							<div class="mt-4 grid gap-3 text-xs">
								{#each inspectorPanel.technical as item (`inspector-tech:${item.label}`)}
									<div class="rounded-xl border bg-muted/15 p-3">
										<p class="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
											{item.label}
										</p>
										<p class="mt-2 font-mono break-all">{item.value}</p>
									</div>
								{/each}
								{#if runDetails}
									<div class="rounded-xl border bg-muted/15 p-3">
										<p class="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
											Plugins
										</p>
										<p class="mt-2 break-words">{runDetails.plugins}</p>
									</div>
									<div class="rounded-xl border bg-muted/15 p-3">
										<p class="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
											Config
										</p>
										<p class="mt-2 font-mono break-all">{runDetails.configHash}</p>
									</div>
									<div class="rounded-xl border bg-muted/15 p-3">
										<p class="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
											Artifacts
										</p>
										<p class="mt-2 font-mono break-all">{runDetails.artifactPath}</p>
									</div>
								{/if}
							</div>
						</details>
					</div>
				{:else if tabValue === 'timeline'}
					<div class="grid gap-3">
						{#if recentChangeItems.length}
							{#each recentChangeItems as item (`change:${item.label}`)}
								<div class="rounded-2xl border bg-background/90 p-4 shadow-sm">
									<div class="flex items-center justify-between gap-3">
										<p class="text-sm font-semibold">{item.label}</p>
										<span
											class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${severityBadgeClass(item.severity)}`}
										>
											{item.severity}
										</span>
									</div>
									<p class="mt-3 text-sm leading-6">{item.summary}</p>
									{#if item.detail}
										<p class="mt-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>
									{/if}
								</div>
							{/each}
						{:else}
							<p class="text-sm text-muted-foreground">
								Pause playback or load more metrics to surface recent changes.
							</p>
						{/if}

						<div class="rounded-2xl border bg-background/90 p-4 shadow-sm">
							<div class="flex flex-wrap items-center justify-between gap-3">
								<div class="min-w-0">
									<p class="text-sm font-semibold">Milestone timeline</p>
									<p class="mt-1 text-xs text-muted-foreground">
										Peaks, threshold crossings, anomalies, and event bursts can jump playback directly.
									</p>
								</div>
								<span class="rounded-full border px-2 py-0.5 text-[11px] font-medium">
									{milestones.length} markers
								</span>
							</div>
							{#if milestones.length}
								<div class="mt-4 grid gap-3 md:grid-cols-2">
									{#each milestones as milestone (milestone.id)}
										<button
											type="button"
											class="min-w-0 rounded-2xl border bg-background/80 p-4 text-left transition hover:bg-muted/35"
											onclick={() => openMilestone(milestone)}
										>
											<div class="flex flex-wrap items-center justify-between gap-2">
												<div class="flex flex-wrap items-center gap-2">
													<span
														class={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${severityBadgeClass(milestone.severity)}`}
													>
														{milestone.kind.replace('_', ' ')}
													</span>
													{#if milestone.metric}
														<span class="inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
															{humanizeIdentifier(milestone.metric)}
														</span>
													{/if}
												</div>
												<span class="text-[11px] text-muted-foreground">
													{formatTimeLabel(milestone.t)}
												</span>
											</div>
											<p class="mt-3 font-medium">{milestone.title}</p>
											<p class="mt-2 text-xs leading-5 text-muted-foreground">{milestone.summary}</p>
											<div class="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
												<span class="inline-flex rounded-full border px-2 py-0.5 font-medium">
													Jump in replay
												</span>
											</div>
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
				{:else if tabValue === 'artifacts'}
					<div class="grid gap-3 text-sm">
						<div class="grid gap-2">
							<!-- eslint-disable svelte/no-navigation-without-resolve -->
							<a class="studio-action-link" href={api.exportRunUrl(data.runId, 'csv')}>CSV export</a>
							<a class="studio-action-link" href={api.exportRunUrl(data.runId, 'parquet')}>Parquet export</a>
							<!-- eslint-enable svelte/no-navigation-without-resolve -->
							<a class="studio-action-link" href={resolve(`/compare?runA=${data.runId}`)}>Compare this run</a>
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
							</Table.TableBody>
						</Table.Table>
					</div>
				{:else if tabValue === 'debug'}
					<div class="grid gap-4">
						<div>
							<p class="mb-3 text-sm font-semibold">Runtime streams</p>
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
										<Table.TableCell class="font-mono text-xs">{metrics.length} metric records</Table.TableCell>
									</Table.TableRow>
								</Table.TableBody>
							</Table.Table>
						</div>
						<div>
							<p class="mb-3 text-sm font-semibold">Run manifest</p>
							<pre class="overflow-auto rounded-md bg-muted p-4 text-xs">{JSON.stringify(run, null, 2)}</pre>
						</div>
					</div>
				{/if}
			{/snippet}
		</RunSecondaryTabs>
	</StudioPanel>
</div>

{#if focusSurface === 'viewport' && currentView.surface === 'viewport'}
	<div class="fixed inset-0 z-50 bg-background/85 p-4 backdrop-blur-sm">
		<div
			role="dialog"
			aria-modal="true"
			aria-labelledby="viewport-fullscreen-title"
			aria-describedby="viewport-fullscreen-description"
			class="flex h-full flex-col gap-4 rounded-2xl border bg-background p-4 shadow-2xl"
		>
			<div class="flex items-center justify-between gap-3">
				<div>
					<p id="viewport-fullscreen-title" class="text-sm font-semibold">
						{currentView.label} full-screen
					</p>
					<p id="viewport-fullscreen-description" class="text-xs text-muted-foreground">
						Playback and selection remain live while this overlay is open.
					</p>
				</div>
				<Button
					bind:ref={viewportDialogCloseButton}
					variant="outline"
					size="sm"
					autofocus
					aria-label="Close full-screen view"
					onclick={() => (focusSurface = 'none')}
				>
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
					viewPurpose={currentView.purpose}
					viewHelp={currentView.help}
					loadingTitle={currentView.loading.title}
					loadingBody={currentView.loading.body}
					emptyTitle={currentView.empty.title}
					emptyBody={currentView.empty.body}
					onSelect={(object) => playback.selectObject(object)}
				/>
			</div>
		</div>
	</div>
{/if}

{#if focusSurface === 'metrics' && focusedMetric}
	<div class="fixed inset-0 z-50 bg-background/85 p-4 backdrop-blur-sm">
		<div
			role="dialog"
			aria-modal="true"
			aria-labelledby="metric-fullscreen-title"
			aria-describedby="metric-fullscreen-description"
			class="flex h-full flex-col gap-4 rounded-2xl border bg-background p-4 shadow-2xl"
		>
			<div class="flex items-center justify-between gap-3">
				<div>
					<p id="metric-fullscreen-title" class="text-sm font-semibold">
						{focusedMetric.label} full-screen analysis
					</p>
					<p id="metric-fullscreen-description" class="text-xs text-muted-foreground">
						Focused metric view keeps threshold markers, events, and frame scrubbing in one place.
					</p>
				</div>
				<Button
					bind:ref={metricDialogCloseButton}
					variant="outline"
					size="sm"
					autofocus
					aria-label="Close full-screen view"
					onclick={() => (focusSurface = 'none')}
				>
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
