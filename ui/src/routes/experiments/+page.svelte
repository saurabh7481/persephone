<script lang="ts">
	import { resolve } from '$app/paths';
	import { AlertCircle, Play } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import {
		PersephoneApi,
		validateExperimentConfigAgainstSchema,
		type ExampleConfigResponse,
		type ExampleSummary,
		type ExperimentConfig,
		type RunSummary
	} from '$lib/api';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Textarea } from '$lib/components/ui/textarea';

	const api = new PersephoneApi();

	let examples = $state<ExampleSummary[]>([]);
	let selectedExampleId = $state('');
	let selectedExample = $state<ExampleConfigResponse | null>(null);
	let configText = $state('');
	let submitting = $state(false);
	let createdRun = $state<RunSummary | null>(null);
	let submitError = $state('');

	const parsedConfig = $derived(parseConfig(configText));
	const schemaErrors = $derived(
		parsedConfig.ok
			? validateExperimentConfigAgainstSchema(parsedConfig.config)
			: [parsedConfig.error]
	);

	onMount(async () => {
		try {
			examples = await api.listExamples();
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

	async function submit() {
		submitError = '';
		createdRun = null;
		if (!parsedConfig.ok || schemaErrors.length) return;
		submitting = true;
		try {
			createdRun = await api.startRun(parsedConfig.config);
		} catch (err) {
			submitError = err instanceof Error ? err.message : 'Unable to start run.';
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
</script>

<div class="grid gap-5 lg:grid-cols-[340px_minmax(0,1fr)]">
	<div class="space-y-5">
		<div>
			<h1 class="text-2xl font-semibold tracking-normal">Experiments</h1>
			<p class="text-sm text-muted-foreground">
				Start from any installed example, then edit the generated run payload.
			</p>
		</div>

		<Card.Card>
			<Card.CardHeader>
				<Card.CardTitle>Example catalog</Card.CardTitle>
				<Card.CardDescription>Examples are presets, not platform assumptions.</Card.CardDescription>
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
			</Card.CardContent>
			<Card.CardFooter class="flex flex-wrap items-center gap-3">
				<Button
					disabled={submitting || !parsedConfig.ok || schemaErrors.length > 0}
					onclick={() => void submit()}
				>
					<Play size={16} />
					Run experiment
				</Button>
				{#if createdRun}
					<a
						class="text-sm font-medium text-primary hover:underline"
						href={resolve(`/runs/${createdRun.run_id}`)}
					>
						{createdRun.run_id}
					</a>
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

	<Card.Card>
		<Card.CardHeader>
			<Card.CardTitle>Run payload</Card.CardTitle>
			<Card.CardDescription>Advanced JSON payload sent to POST /runs.</Card.CardDescription>
		</Card.CardHeader>
		<Card.CardContent>
			<Textarea class="min-h-[620px] font-mono text-xs" bind:value={configText} />
		</Card.CardContent>
	</Card.Card>
</div>
