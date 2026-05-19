<script lang="ts">
	import { resolve } from '$app/paths';
	import { AlertCircle, Play } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import {
		PersephoneApi,
		buildSirExampleConfig,
		parseInitialInfected,
		validateExperimentConfigAgainstSchema,
		validateSirValues,
		type RunSummary
	} from '$lib/api';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';

	const api = new PersephoneApi();

	let seed = $state(42);
	let tEnd = $state(24);
	let pInfect = $state(0.6);
	let pRecover = $state(0.08);
	let initiallyInfected = $state('0, 10');
	let submitting = $state(false);
	let createdRun = $state<RunSummary | null>(null);
	let submitError = $state('');

	const values = $derived({
		seed,
		tEnd,
		pInfect,
		pRecover,
		initiallyInfected: parseInitialInfected(initiallyInfected)
	});
	const errors = $derived(validateSirValues(values));
	const config = $derived(buildSirExampleConfig(values));
	const schemaErrors = $derived(validateExperimentConfigAgainstSchema(config));

	onMount(async () => {
		try {
			const example = await api.getSirExampleConfig();
			seed = example.seed;
			tEnd = example.scheduler.t_end;
			pInfect = example.solvers[0]?.params.p_infect ?? pInfect;
			pRecover = example.solvers[0]?.params.p_recover ?? pRecover;
			initiallyInfected = (example.solvers[0]?.params.initially_infected ?? [0, 10]).join(', ');
		} catch {
			// The local UI still works with its bundled defaults when the API is offline.
		}
	});

	async function submit() {
		submitError = '';
		createdRun = null;
		if (errors.length || schemaErrors.length) return;
		submitting = true;
		try {
			createdRun = await api.startRun(config);
		} catch (err) {
			submitError = err instanceof Error ? err.message : 'Unable to start run.';
		} finally {
			submitting = false;
		}
	}
</script>

<div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
	<div class="space-y-5">
		<div>
			<h1 class="text-2xl font-semibold tracking-normal">Experiments</h1>
			<p class="text-sm text-muted-foreground">
				Edit the bundled SIR example and start a local run.
			</p>
		</div>

		<Card.Card>
			<Card.CardHeader>
				<Card.CardTitle>SIR example config</Card.CardTitle>
				<Card.CardDescription
					>20-node contact network with infection and recovery parameters.</Card.CardDescription
				>
			</Card.CardHeader>
			<Card.CardContent>
				<form class="grid gap-4 sm:grid-cols-2" onsubmit={(event) => event.preventDefault()}>
					<label class="grid gap-2 text-sm font-medium">
						Seed
						<Input type="number" bind:value={seed} />
					</label>
					<label class="grid gap-2 text-sm font-medium">
						Duration
						<Input type="number" min="1" bind:value={tEnd} />
					</label>
					<label class="grid gap-2 text-sm font-medium">
						Infection probability
						<Input type="number" min="0" max="1" step="0.01" bind:value={pInfect} />
					</label>
					<label class="grid gap-2 text-sm font-medium">
						Recovery probability
						<Input type="number" min="0" max="1" step="0.01" bind:value={pRecover} />
					</label>
					<label class="grid gap-2 text-sm font-medium sm:col-span-2">
						Initially infected nodes
						<Input bind:value={initiallyInfected} />
					</label>
				</form>

				{#if errors.length || schemaErrors.length}
					<Alert.Alert variant="destructive" class="mt-4">
						<AlertCircle size={16} />
						<Alert.AlertTitle>Validation</Alert.AlertTitle>
						<Alert.AlertDescription>{[...errors, ...schemaErrors].join(' ')}</Alert.AlertDescription
						>
					</Alert.Alert>
				{/if}
			</Card.CardContent>
			<Card.CardFooter class="flex flex-wrap items-center gap-3">
				<Button
					disabled={submitting || errors.length > 0 || schemaErrors.length > 0}
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
			<Card.CardTitle>Config preview</Card.CardTitle>
			<Card.CardDescription>Payload sent to `POST /runs`.</Card.CardDescription>
		</Card.CardHeader>
		<Card.CardContent>
			<Textarea
				class="min-h-[520px] font-mono text-xs"
				readonly
				value={JSON.stringify(config, null, 2)}
			/>
		</Card.CardContent>
	</Card.Card>
</div>
