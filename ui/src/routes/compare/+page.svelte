<script lang="ts">
	import { AlertCircle, GitCompareArrows } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import { PersephoneApi, type CompareResult } from '$lib/api';
	import ComparisonChart from '$lib/components/ComparisonChart.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import * as Table from '$lib/components/ui/table';

	const api = new PersephoneApi();

	let runA = $state('');
	let runB = $state('');
	let metric = $state('');
	let loading = $state(false);
	let error = $state('');
	let result = $state<CompareResult | null>(null);

	onMount(() => {
		const params = new URLSearchParams(location.search);
		runA = params.get('runA') ?? runA;
		runB = params.get('runB') ?? runB;
		metric = params.get('metric') ?? metric;
	});

	async function submit() {
		error = '';
		result = null;
		if (!runA || !runB || !metric) {
			error = 'Both run ids and a metric are required.';
			return;
		}
		loading = true;
		try {
			result = await api.compareRuns(runA, runB, metric);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unable to compare runs.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="space-y-5">
	<div>
		<h1 class="text-2xl font-semibold tracking-normal">Compare</h1>
		<p class="text-sm text-muted-foreground">Overlay one metric across two completed runs.</p>
	</div>

	<Card.Card>
		<Card.CardHeader>
			<Card.CardTitle>Run pair</Card.CardTitle>
		</Card.CardHeader>
		<Card.CardContent>
			<form
				class="grid gap-4 md:grid-cols-[1fr_1fr_1fr_auto]"
				onsubmit={(event) => event.preventDefault()}
			>
				<label class="grid gap-2 text-sm font-medium">
					Run A
					<Input bind:value={runA} />
				</label>
				<label class="grid gap-2 text-sm font-medium">
					Run B
					<Input bind:value={runB} />
				</label>
				<label class="grid gap-2 text-sm font-medium">
					Metric
					<Input bind:value={metric} />
				</label>
				<div class="flex items-end">
					<Button disabled={loading} onclick={() => void submit()}>
						<GitCompareArrows size={16} />
						Compare runs
					</Button>
				</div>
			</form>
		</Card.CardContent>
	</Card.Card>

	{#if error}
		<Alert.Alert variant="destructive">
			<AlertCircle size={16} />
			<Alert.AlertTitle>Compare failed</Alert.AlertTitle>
			<Alert.AlertDescription>{error}</Alert.AlertDescription>
		</Alert.Alert>
	{/if}

	<Card.Card>
		<Card.CardHeader>
			<Card.CardTitle>{result?.metric ?? metric}</Card.CardTitle>
			<Card.CardDescription>Overlay chart aligned by logical simulation time.</Card.CardDescription>
		</Card.CardHeader>
		<Card.CardContent class="space-y-5">
			<ComparisonChart rows={result?.aligned ?? []} />
			{#if result}
				<div class="grid gap-3 md:grid-cols-2">
					{#each [result.run_a, result.run_b] as runId (runId)}
						<div class="rounded-md border p-3">
							<p class="studio-eyebrow">{runId === result.run_a ? 'Run A' : 'Run B'}</p>
							<p class="mt-1 font-mono text-sm">{runId}</p>
							<p class="mt-1 text-xs text-muted-foreground">
								Peak {result.summaries[runId]?.peak ?? 0} · Final {result.summaries[runId]?.final ??
									0}
							</p>
						</div>
					{/each}
				</div>
				<Table.Table>
					<Table.TableHeader>
						<Table.TableRow>
							<Table.TableHead>Run</Table.TableHead>
							<Table.TableHead>Peak</Table.TableHead>
							<Table.TableHead>Final</Table.TableHead>
							<Table.TableHead>AUC</Table.TableHead>
						</Table.TableRow>
					</Table.TableHeader>
					<Table.TableBody>
						{#each [result.run_a, result.run_b] as runId (runId)}
							<Table.TableRow>
								<Table.TableCell>{runId}</Table.TableCell>
								<Table.TableCell>{result.summaries[runId]?.peak ?? 0}</Table.TableCell>
								<Table.TableCell>{result.summaries[runId]?.final ?? 0}</Table.TableCell>
								<Table.TableCell>{result.summaries[runId]?.auc ?? 0}</Table.TableCell>
							</Table.TableRow>
						{/each}
					</Table.TableBody>
				</Table.Table>
				<div class="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
					Frame comparison placeholder: synchronized side-by-side playback will use the same frame
					renderers once multi-run visual overlays are available.
				</div>
			{/if}
		</Card.CardContent>
	</Card.Card>
</div>
