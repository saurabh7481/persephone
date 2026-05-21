<script lang="ts">
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import {
		AlertCircle,
		CirclePause,
		CirclePlay,
		Rewind,
		SkipBack,
		SkipForward
	} from '@lucide/svelte';

	import {
		PersephoneApi,
		compareMetricSummary,
		type EventRecord,
		type FieldArtifactSummary,
		type MetricRecord,
		type RunSummary
	} from '$lib/api';
	import MetricTimeline from '$lib/components/MetricTimeline.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { SimulationViewport, StudioPanel, StudioWorkbench } from '$lib/components/studio';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Table from '$lib/components/ui/table';
	import * as Tabs from '$lib/components/ui/tabs';
	import { createPlaybackStore, playbackSourceFromApi } from '$lib/studio/playback';
	import {
		artifactSummaries,
		fieldCellInspection,
		graphNodeInspection,
		runInspection
	} from '$lib/studio/inspector';

	let { data }: { data: { runId: string } } = $props();
	const api = new PersephoneApi();
	const playback = createPlaybackStore({ source: playbackSourceFromApi(api) });

	let run = $state<RunSummary | null>(null);
	let metrics = $state<MetricRecord[]>([]);
	let events = $state<EventRecord[]>([]);
	let fieldArtifacts = $state<FieldArtifactSummary[]>([]);
	let error = $state('');
	let streamState = $state<'idle' | 'connected' | 'closed'>('idle');

	const summary = $derived(compareMetricSummary(metrics));
	const selectedFrame = $derived(
		$playback.frameBuffer.find((frame) => frame.frame_id === $playback.selectedFrameId) ?? null
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
			events
		)
	);
	const artifacts = $derived(artifactSummaries(run, metrics, events, $playback.frameBuffer));

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
			run = await api.getRun(data.runId);
		} catch {
			// Existing metrics remain useful if a transient refresh fails.
		}
	}

	function metricKey(record: MetricRecord): string {
		return `${record.t}:${record.metric}:${record.value}`;
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
		if (target?.matches('input, textarea, select, [contenteditable="true"]')) return;
		if (event.key === ' ') {
			event.preventDefault();
			togglePlayback();
		}
		if (event.key === 'ArrowLeft') {
			event.preventDefault();
			playback.scrubTo(Math.max(0, $playback.currentTime - 1));
		}
		if (event.key === 'ArrowRight') {
			event.preventDefault();
			playback.scrubTo($playback.currentTime + 1);
		}
	}
</script>

<svelte:window onkeydown={handleRunKeydown} />

<StudioWorkbench
	title={data.runId}
	subtitle="Live playback, replay frames, metrics, events, and run metadata."
>
	{#snippet left()}
		<div class="grid gap-3 p-3">
			<StudioPanel title="Run context">
				<div class="grid gap-3 text-sm">
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
						<span class="text-muted-foreground">Metric stream</span>
						<span>{streamState}</span>
					</div>
				</div>
			</StudioPanel>

			<StudioPanel title="Playback controls">
				<div class="grid gap-2">
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
							aria-label="Pause playback"
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
						Speed
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
		</div>
	{/snippet}

	{#snippet viewport()}
		{#if error}
			<Alert.Alert variant="destructive" class="m-3">
				<AlertCircle size={16} />
				<Alert.AlertTitle>Run unavailable</Alert.AlertTitle>
				<Alert.AlertDescription>{error}</Alert.AlertDescription>
			</Alert.Alert>
		{:else}
			<SimulationViewport
				frame={selectedFrame}
				mode={$playback.mode}
				status={$playback.status}
				speed={$playback.speed}
				bufferedFrames={$playback.frameBuffer.length}
				selectedObject={$playback.selectedObject}
				onSelect={(object) => playback.selectObject(object)}
			/>
		{/if}
	{/snippet}

	{#snippet inspector()}
		<div class="grid gap-3 p-3">
			<StudioPanel title="Inspector">
				<div class="grid gap-2 text-sm">
					<div>
						<p class="text-xs text-muted-foreground">Selected frame</p>
						<p class="font-mono text-xs break-all">{selectedFrame?.frame_id ?? 'none'}</p>
					</div>
					<div>
						<p class="text-xs text-muted-foreground">Kind</p>
						<p>{selectedFrame?.kind ?? '-'}</p>
					</div>
					<div>
						<p class="text-xs text-muted-foreground">Solver</p>
						<p class="font-mono text-xs break-all">{selectedFrame?.solver_id ?? '-'}</p>
					</div>
					<div>
						<p class="text-xs text-muted-foreground">Selected object</p>
						<p class="font-mono text-xs break-all">
							{selectedObject ? `${selectedObject.kind}:${selectedObject.id}` : 'none'}
						</p>
					</div>
					{#if fieldCellDetails}
						<div class="rounded-md border p-3">
							<p class="studio-eyebrow">Field cell</p>
							<p class="mt-2 font-mono text-xs">
								{fieldCellDetails.field}[{fieldCellDetails.row}, {fieldCellDetails.column}]
							</p>
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
						<div class="rounded-md border p-3">
							<p class="studio-eyebrow">Graph node</p>
							<p class="mt-2 font-mono text-xs">{graphNodeDetails.id}</p>
							<p class="text-sm">{graphNodeDetails.state} · degree {graphNodeDetails.degree}</p>
							<p class="mt-1 text-xs text-muted-foreground">
								{graphNodeDetails.events.length} related events
							</p>
						</div>
					{/if}
					{#if runDetails}
						<details class="rounded-md border p-3">
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
					<div class="rounded-md border p-3">
						<p class="studio-eyebrow">Visualization</p>
						<p class="mt-2 text-xs text-muted-foreground">
							Palette, autoscale, bounds, opacity, and layer controls live in the viewport overlay.
						</p>
					</div>
				</div>
			</StudioPanel>
		</div>
	{/snippet}

	{#snippet dock()}
		<div class="p-3">
			<Tabs.Tabs value="metrics" class="space-y-4">
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
							<p class="text-2xl font-semibold">{$playback.currentTime.toFixed(2)}</p>
						</StudioPanel>
						<StudioPanel title="Current frame">
							<p class="truncate text-2xl font-semibold">{selectedFrame?.frame_id ?? '-'}</p>
						</StudioPanel>
						<StudioPanel title="Peak value">
							<p class="text-2xl font-semibold">{summary.peakValue}</p>
						</StudioPanel>
						<StudioPanel title="Final value">
							<p class="text-2xl font-semibold">{summary.finalValue}</p>
						</StudioPanel>
						<StudioPanel title="Elapsed time">
							<p class="text-2xl font-semibold">{summary.duration}</p>
						</StudioPanel>
					</div>
					<StudioPanel
						title="Metric timeline"
						description="Metrics, events, and frame ticks synchronized with playback time."
					>
						<MetricTimeline
							records={metrics}
							{events}
							frames={$playback.frameBuffer}
							selectedTime={$playback.currentTime}
							onSelectTime={(time) => playback.scrubTo(time)}
						/>
					</StudioPanel>
				</Tabs.TabsContent>

				<Tabs.TabsContent value="events">
					<StudioPanel title="Event log">
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
										<Table.TableCell>{event.t ?? '-'}</Table.TableCell>
										<Table.TableCell>{event.event_type ?? event.type ?? '-'}</Table.TableCell>
										<Table.TableCell class="font-mono text-xs">
											{JSON.stringify(event)}
										</Table.TableCell>
									</Table.TableRow>
								{/each}
							</Table.TableBody>
						</Table.Table>
					</StudioPanel>
				</Tabs.TabsContent>

				<Tabs.TabsContent value="frames">
					<StudioPanel title="Frame buffer" description="Replay and live frames share this buffer.">
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
										<Table.TableCell>{frame.t}</Table.TableCell>
									</Table.TableRow>
								{/each}
							</Table.TableBody>
						</Table.Table>
					</StudioPanel>
				</Tabs.TabsContent>

				<Tabs.TabsContent value="artifacts">
					<StudioPanel title="Artifacts" description="Run outputs, exports, and replay payloads.">
						<div class="mb-3 flex flex-wrap gap-2">
							<!-- eslint-disable svelte/no-navigation-without-resolve -->
							<a class="studio-action-link" href={api.exportRunUrl(data.runId, 'csv')}>CSV export</a
							>
							<a class="studio-action-link" href={api.exportRunUrl(data.runId, 'parquet')}>
								Parquet export
							</a>
							<!-- eslint-enable svelte/no-navigation-without-resolve -->
							<a class="studio-action-link" href={resolve(`/compare?runA=${data.runId}`)}>
								Compare this run
							</a>
							{#if selectedFrame}
								<!-- eslint-disable svelte/no-navigation-without-resolve -->
								<a
									class="studio-action-link"
									href={api.frameUrl(data.runId, selectedFrame.frame_id)}
								>
									Field frame export
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
											<a class="font-medium text-primary hover:underline" href={artifact.href}
												>Open</a
											>
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
					</StudioPanel>
				</Tabs.TabsContent>

				<Tabs.TabsContent value="logs">
					<StudioPanel title="Logs">
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
					</StudioPanel>
				</Tabs.TabsContent>

				<Tabs.TabsContent value="manifest">
					<StudioPanel title="Manifest summary">
						<pre class="overflow-auto rounded-md bg-muted p-4 text-xs">{JSON.stringify(
								run,
								null,
								2
							)}</pre>
					</StudioPanel>
				</Tabs.TabsContent>
			</Tabs.Tabs>
		</div>
	{/snippet}
</StudioWorkbench>
