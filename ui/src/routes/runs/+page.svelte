<script lang="ts">
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { AlertCircle, RefreshCw } from '@lucide/svelte';

	import { PersephoneApi, type RunSummary } from '$lib/api';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import * as Alert from '$lib/components/ui/alert';

	const api = new PersephoneApi();

	let runs = $state<RunSummary[]>([]);
	let loading = $state(true);
	let error = $state('');

	async function loadRuns() {
		loading = true;
		error = '';
		try {
			runs = await api.listRuns();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unable to load runs.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		void loadRuns();
	});

	function formatStarted(value: string): string {
		if (!value) return '-';
		return new Intl.DateTimeFormat(undefined, {
			dateStyle: 'medium',
			timeStyle: 'short'
		}).format(new Date(value));
	}
</script>

<div class="space-y-5">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<h1 class="text-2xl font-semibold tracking-normal">Runs</h1>
			<p class="text-sm text-muted-foreground">Local simulation history and active work.</p>
		</div>
		<Button variant="outline" onclick={() => void loadRuns()}>
			<RefreshCw size={16} />
			Refresh
		</Button>
	</div>

	{#if error}
		<Alert.Alert variant="destructive">
			<AlertCircle size={16} />
			<Alert.AlertTitle>API unavailable</Alert.AlertTitle>
			<Alert.AlertDescription>{error}</Alert.AlertDescription>
		</Alert.Alert>
	{/if}

	<Card.Card>
		<Card.CardHeader>
			<Card.CardTitle>Run catalog</Card.CardTitle>
			<Card.CardDescription
				>Discovered from the local Persephone artifact catalog.</Card.CardDescription
			>
		</Card.CardHeader>
		<Card.CardContent>
			{#if loading}
				<div class="space-y-2">
					<div class="h-10 rounded-md bg-muted"></div>
					<div class="h-10 rounded-md bg-muted"></div>
					<div class="h-10 rounded-md bg-muted"></div>
				</div>
			{:else if runs.length === 0}
				<div class="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
					No runs found.
				</div>
			{:else}
				<div class="overflow-x-auto">
					<Table.Table>
						<Table.TableHeader>
							<Table.TableRow>
								<Table.TableHead>Run</Table.TableHead>
								<Table.TableHead>Status</Table.TableHead>
								<Table.TableHead>Experiment</Table.TableHead>
								<Table.TableHead>Plugin</Table.TableHead>
								<Table.TableHead>Started</Table.TableHead>
								<Table.TableHead>Final time</Table.TableHead>
								<Table.TableHead>Artifacts</Table.TableHead>
							</Table.TableRow>
						</Table.TableHeader>
						<Table.TableBody>
							{#each runs as run (run.run_id)}
								<Table.TableRow>
									<Table.TableCell>
										<a
											class="font-medium text-primary hover:underline"
											href={resolve(`/runs/${run.run_id}`)}
										>
											{run.run_id}
										</a>
									</Table.TableCell>
									<Table.TableCell><StatusBadge status={run.status} /></Table.TableCell>
									<Table.TableCell>{run.name || '-'}</Table.TableCell>
									<Table.TableCell>{run.plugins.join(', ') || '-'}</Table.TableCell>
									<Table.TableCell>{formatStarted(run.started_at)}</Table.TableCell>
									<Table.TableCell>{run.final_time}</Table.TableCell>
									<Table.TableCell class="font-mono text-xs"
										>{run.artifact_path ?? '-'}</Table.TableCell
									>
								</Table.TableRow>
							{/each}
						</Table.TableBody>
					</Table.Table>
				</div>
			{/if}
		</Card.CardContent>
	</Card.Card>
</div>
