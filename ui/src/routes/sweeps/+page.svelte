<script lang="ts">
	import { resolve } from '$app/paths';
	import { AlertCircle, Play } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import {
		PersephoneApi,
		sweepValuesFromText,
		type ExperimentConfig,
		type SweepManifest
	} from '$lib/api';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import * as Table from '$lib/components/ui/table';

	const api = new PersephoneApi();

	let parameter = $state('');
	let values = $state('');
	let running = $state(false);
	let error = $state('');
	let manifest = $state<SweepManifest | null>(null);
	let baseConfig = $state<ExperimentConfig | null>(null);

	onMount(async () => {
		try {
			const examples = await api.listExamples();
			const example = examples[0] ? await api.getExampleConfig(examples[0].id) : null;
			baseConfig = example?.config ?? null;
		} catch {
			// The page reports the missing base config in the form validation below.
		}
	});

	async function submit() {
		error = '';
		manifest = null;
		const parsedValues = sweepValuesFromText(values);
		if (!baseConfig || !parameter || parsedValues.length === 0) {
			error = 'Base config, parameter, and at least one sweep value are required.';
			return;
		}
		running = true;
		try {
			manifest = await api.startSweep({
				name: 'Scalar parameter sweep',
				base_config: baseConfig,
				parameter,
				values: parsedValues
			});
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unable to run sweep.';
		} finally {
			running = false;
		}
	}
</script>

<div class="grid gap-5 lg:grid-cols-[minmax(0,460px)_1fr]">
	<div class="space-y-5">
		<div>
			<h1 class="text-2xl font-semibold tracking-normal">Sweeps</h1>
			<p class="text-sm text-muted-foreground">Run one scalar parameter across multiple values.</p>
		</div>

		<Card.Card>
			<Card.CardHeader>
				<Card.CardTitle>Scalar parameter</Card.CardTitle>
				<Card.CardDescription
					>Uses the first available example as the base config.</Card.CardDescription
				>
			</Card.CardHeader>
			<Card.CardContent class="space-y-4">
				<label class="grid gap-2 text-sm font-medium">
					Parameter path
					<Input bind:value={parameter} />
				</label>
				<label class="grid gap-2 text-sm font-medium">
					Sweep values
					<Input bind:value={values} />
				</label>
			</Card.CardContent>
			<Card.CardFooter>
				<Button disabled={running} onclick={() => void submit()}>
					<Play size={16} />
					Run sweep
				</Button>
			</Card.CardFooter>
		</Card.Card>

		{#if error}
			<Alert.Alert variant="destructive">
				<AlertCircle size={16} />
				<Alert.AlertTitle>Sweep failed</Alert.AlertTitle>
				<Alert.AlertDescription>{error}</Alert.AlertDescription>
			</Alert.Alert>
		{/if}
	</div>

	<Card.Card>
		<Card.CardHeader>
			<Card.CardTitle>Sweep result</Card.CardTitle>
			<Card.CardDescription>Sequential child runs linked by sweep manifest.</Card.CardDescription>
		</Card.CardHeader>
		<Card.CardContent>
			{#if manifest}
				<div class="mb-4 text-sm">
					<span class="font-medium">{manifest.sweep_id}</span>
					<span class="text-muted-foreground"> · {manifest.parameter}</span>
				</div>
				<Table.Table>
					<Table.TableHeader>
						<Table.TableRow>
							<Table.TableHead>Run</Table.TableHead>
							<Table.TableHead>Value</Table.TableHead>
							<Table.TableHead>Status</Table.TableHead>
						</Table.TableRow>
					</Table.TableHeader>
					<Table.TableBody>
						{#each manifest.child_runs as child (child.run_id)}
							<Table.TableRow>
								<Table.TableCell>
									<a
										class="font-medium text-primary hover:underline"
										href={resolve(`/runs/${child.run_id}`)}>{child.run_id}</a
									>
								</Table.TableCell>
								<Table.TableCell>{child.value}</Table.TableCell>
								<Table.TableCell>{child.status}</Table.TableCell>
							</Table.TableRow>
						{/each}
					</Table.TableBody>
				</Table.Table>
			{:else}
				<div class="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
					No sweep has been run yet.
				</div>
			{/if}
		</Card.CardContent>
	</Card.Card>
</div>
