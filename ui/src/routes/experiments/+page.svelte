<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { AlertCircle, Code2, FlaskConical, Play, SlidersHorizontal } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import {
		PersephoneApi,
		type ExampleConfigResponse,
		type ExampleSummary,
		type ExperimentConfig,
		type PluginSummary,
		type RunSummary
	} from '$lib/api';
	import {
		assignConfigPath,
		coerceScalarValue,
		scalarParameterPaths,
		validateBuilderConfig
	} from '$lib/studio/experiment-builder';
	import { pushToast } from '$lib/studio/toasts';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Textarea } from '$lib/components/ui/textarea';

	const api = new PersephoneApi();

	let examples = $state<ExampleSummary[]>([]);
	let plugins = $state<PluginSummary[]>([]);
	let selectedExampleId = $state('');
	let selectedExample = $state<ExampleConfigResponse | null>(null);
	let configText = $state('');
	let submitting = $state(false);
	let createdRun = $state<RunSummary | null>(null);
	let submitError = $state('');

	const parsedConfig = $derived(parseConfig(configText));
	const schemaErrors = $derived(
		parsedConfig.ok ? validateBuilderConfig(parsedConfig.config) : [parsedConfig.error]
	);
	const config = $derived(parsedConfig.ok ? parsedConfig.config : null);
	const scalarPaths = $derived(
		config && schemaErrors.length === 0 ? scalarParameterPaths(config) : []
	);
	const selectedPluginName = $derived(config?.solvers?.[0]?.plugin ?? selectedExampleId);

	onMount(async () => {
		try {
			[examples, plugins] = await Promise.all([api.listExamples(), api.listPlugins()]);
			selectedExampleId = examples[0]?.id ?? '';
			if (selectedExampleId) await loadExample(selectedExampleId);
		} catch (err) {
			submitError = err instanceof Error ? err.message : 'Unable to load examples.';
		}
	});

	async function loadExample(exampleId: string) {
		selectedExampleId = exampleId;
		selectedExample = await api.getExampleConfig(exampleId);
		configText = JSON.stringify(selectedExample.config, null, 2);
		createdRun = null;
		submitError = '';
	}

	async function selectPlugin(plugin: PluginSummary) {
		const matchingExample = examples.find(
			(example) => example.id === plugin.name || example.id.replaceAll('-', '_') === plugin.name
		);
		if (matchingExample) {
			await loadExample(matchingExample.id);
			return;
		}
		if (!config?.solvers?.[0]) return;
		let next = assignConfigPath(config, 'solvers[0].plugin', plugin.name);
		next = assignConfigPath(next, 'solvers[0].version', `>=${plugin.version}`);
		next = assignConfigPath(next, 'solvers[0].type', plugin.paradigm);
		selectedExampleId = '';
		selectedExample = null;
		configText = JSON.stringify(next, null, 2);
		submitError = '';
		createdRun = null;
	}

	async function submit() {
		submitError = '';
		createdRun = null;
		if (!parsedConfig.ok || schemaErrors.length) return;
		submitting = true;
		try {
			createdRun = await api.startRun(parsedConfig.config);
			pushToast({
				title: 'Run started',
				description: createdRun.run_id,
				tone: 'success'
			});
			await goto(resolve(`/runs/${createdRun.run_id}`));
		} catch (err) {
			submitError = err instanceof Error ? err.message : 'Unable to start run.';
			pushToast({ title: 'Run failed', description: submitError, tone: 'error' });
		} finally {
			submitting = false;
		}
	}

	function parseConfig(
		text: string
	): { ok: true; config: ExperimentConfig } | { ok: false; error: string } {
		try {
			return { ok: true, config: JSON.parse(text) as ExperimentConfig };
		} catch {
			return { ok: false, error: 'Config must be valid JSON.' };
		}
	}

	function updateConfig(path: string, value: string | number | boolean) {
		if (!config) return;
		const next = assignConfigPath(config, path, value);
		configText = JSON.stringify(next, null, 2);
	}

	function updateScalar(path: string, rawValue: string, original: string | number | boolean) {
		updateConfig(path, coerceScalarValue(rawValue, original));
	}
</script>

<div class="grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
	<div class="space-y-5">
		<div>
			<h1 class="text-2xl font-semibold tracking-normal">Experiments</h1>
			<p class="text-sm text-muted-foreground">
				Pick a plugin preset, tune friendly parameters, and run straight into playback.
			</p>
		</div>

		<Card.Card>
			<Card.CardHeader>
				<Card.CardTitle>Plugin selection</Card.CardTitle>
				<Card.CardDescription
					>Examples are presets backed by installed plugins.</Card.CardDescription
				>
			</Card.CardHeader>
			<Card.CardContent class="grid gap-3">
				{#each examples as example (example.id)}
					<Button
						variant={selectedExampleId === example.id ? 'default' : 'outline'}
						onclick={() => void loadExample(example.id)}
					>
						{example.name}
					</Button>
				{/each}
				{#if selectedExample}
					<p class="text-sm text-muted-foreground">{selectedExample.description}</p>
				{/if}
				<div class="rounded-md border bg-muted/40 p-3 text-sm">
					<p class="text-xs font-semibold text-muted-foreground uppercase">Installed plugins</p>
					<div class="mt-2 flex flex-wrap gap-2">
						{#each plugins as plugin (plugin.name)}
							<Button
								type="button"
								variant={plugin.name === selectedPluginName ? 'default' : 'outline'}
								size="sm"
								aria-pressed={plugin.name === selectedPluginName}
								onclick={() => void selectPlugin(plugin)}
							>
								{plugin.name} · {plugin.paradigm}
							</Button>
						{/each}
					</div>
				</div>
			</Card.CardContent>
			<Card.CardFooter class="flex flex-wrap items-center gap-3">
				<Button
					disabled={submitting || !parsedConfig.ok || schemaErrors.length > 0}
					onclick={() => void submit()}
				>
					<Play size={16} />
					Run experiment
				</Button>
				{#if submitting}
					<span class="text-sm text-muted-foreground">Opening live playback...</span>
				{:else if createdRun}
					<span class="text-sm text-muted-foreground">Created {createdRun.run_id}</span>
				{/if}
			</Card.CardFooter>
		</Card.Card>

		{#if schemaErrors.length}
			<Alert.Alert variant="destructive">
				<AlertCircle size={16} />
				<Alert.AlertTitle>Validation</Alert.AlertTitle>
				<Alert.AlertDescription>{schemaErrors.join(' ')}</Alert.AlertDescription>
			</Alert.Alert>
		{/if}

		{#if submitError}
			<Alert.Alert variant="destructive">
				<AlertCircle size={16} />
				<Alert.AlertTitle>Run failed</Alert.AlertTitle>
				<Alert.AlertDescription>{submitError}</Alert.AlertDescription>
			</Alert.Alert>
		{/if}
	</div>

	<Tabs.Tabs value="friendly" class="space-y-4">
		<Tabs.TabsList>
			<Tabs.TabsTrigger value="friendly"
				><SlidersHorizontal size={14} /> Parameters</Tabs.TabsTrigger
			>
			<Tabs.TabsTrigger value="advanced"><Code2 size={14} /> Advanced JSON</Tabs.TabsTrigger>
		</Tabs.TabsList>

		<Tabs.TabsContent value="friendly">
			<Card.Card>
				<Card.CardHeader>
					<Card.CardTitle>Parameter form</Card.CardTitle>
					<Card.CardDescription>
						Generated from the selected preset config and plugin parameter values.
					</Card.CardDescription>
				</Card.CardHeader>
				<Card.CardContent class="grid gap-4 md:grid-cols-2">
					<label class="grid gap-2 text-sm font-medium">
						Experiment name
						<Input
							value={config?.name ?? ''}
							oninput={(event) => updateConfig('name', event.currentTarget.value)}
						/>
					</label>
					<label class="grid gap-2 text-sm font-medium">
						Primary plugin
						<Input value={selectedPluginName ?? ''} disabled />
					</label>
					{#each scalarPaths as item (item.path)}
						<label class="grid gap-2 text-sm font-medium">
							<span class="flex items-center gap-2">
								<FlaskConical size={14} />
								{item.label}
							</span>
							{#if item.type === 'boolean'}
								<select
									class="h-9 rounded-md border bg-background px-2 text-sm"
									value={String(item.value)}
									onchange={(event) =>
										updateScalar(item.path, event.currentTarget.value, item.value)}
								>
									<option value="true">Enabled</option>
									<option value="false">Disabled</option>
								</select>
							{:else}
								<Input
									type={item.type === 'number' ? 'number' : 'text'}
									step="any"
									value={String(item.value)}
									oninput={(event) =>
										updateScalar(item.path, event.currentTarget.value, item.value)}
								/>
							{/if}
							<span class="font-mono text-xs text-muted-foreground">{item.path}</span>
						</label>
					{/each}
				</Card.CardContent>
			</Card.Card>
		</Tabs.TabsContent>

		<Tabs.TabsContent value="advanced">
			<Card.Card>
				<Card.CardHeader>
					<Card.CardTitle>Run payload</Card.CardTitle>
					<Card.CardDescription>Advanced JSON payload sent to POST /runs.</Card.CardDescription>
				</Card.CardHeader>
				<Card.CardContent>
					<Textarea
						aria-label="Run payload"
						class="min-h-[620px] font-mono text-xs"
						bind:value={configText}
					/>
				</Card.CardContent>
			</Card.Card>
		</Tabs.TabsContent>
	</Tabs.Tabs>
</div>
