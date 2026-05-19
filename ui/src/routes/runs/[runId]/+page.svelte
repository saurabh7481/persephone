<script lang="ts">
	import { onMount } from 'svelte';
	import { AlertCircle } from '@lucide/svelte';

	import { PersephoneApi, type EventRecord, type MetricRecord, type RunSummary } from '$lib/api';
	import MetricChart from '$lib/components/MetricChart.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import * as Tabs from '$lib/components/ui/tabs';

	let { data }: { data: { runId: string } } = $props();
	const api = new PersephoneApi();

	let run = $state<RunSummary | null>(null);
	let metrics = $state<MetricRecord[]>([]);
	let events = $state<EventRecord[]>([]);
	let error = $state('');

	onMount(async () => {
		try {
			const [runResult, metricResult, eventResult] = await Promise.all([
				api.getRun(data.runId),
				api.getMetrics(data.runId),
				api.getEvents(data.runId)
			]);
			run = runResult;
			metrics = metricResult;
			events = eventResult;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unable to load run.';
		}
	});
</script>

<div class="space-y-5">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="text-2xl font-semibold tracking-normal">{data.runId}</h1>
			<p class="text-sm text-muted-foreground">Run detail, metrics, and emitted events.</p>
		</div>
		{#if run}
			<StatusBadge status={run.status} />
		{/if}
	</div>

	{#if error}
		<Alert.Alert variant="destructive">
			<AlertCircle size={16} />
			<Alert.AlertTitle>Run unavailable</Alert.AlertTitle>
			<Alert.AlertDescription>{error}</Alert.AlertDescription>
		</Alert.Alert>
	{/if}

	<Tabs.Tabs value="metrics" class="space-y-4">
		<Tabs.TabsList>
			<Tabs.TabsTrigger value="metrics">Metrics</Tabs.TabsTrigger>
			<Tabs.TabsTrigger value="events">Events</Tabs.TabsTrigger>
			<Tabs.TabsTrigger value="manifest">Manifest</Tabs.TabsTrigger>
		</Tabs.TabsList>

		<Tabs.TabsContent value="metrics">
			<Card.Card>
				<Card.CardHeader>
					<Card.CardTitle>Metric chart</Card.CardTitle>
					<Card.CardDescription>SIR population counts over simulation time.</Card.CardDescription>
				</Card.CardHeader>
				<Card.CardContent>
					<MetricChart records={metrics} />
				</Card.CardContent>
			</Card.Card>
		</Tabs.TabsContent>

		<Tabs.TabsContent value="events">
			<Card.Card>
				<Card.CardHeader>
					<Card.CardTitle>Event log</Card.CardTitle>
				</Card.CardHeader>
				<Card.CardContent>
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
				</Card.CardContent>
			</Card.Card>
		</Tabs.TabsContent>

		<Tabs.TabsContent value="manifest">
			<Card.Card>
				<Card.CardHeader>
					<Card.CardTitle>Manifest summary</Card.CardTitle>
				</Card.CardHeader>
				<Card.CardContent>
					<pre class="overflow-auto rounded-md bg-muted p-4 text-xs">{JSON.stringify(
							run,
							null,
							2
						)}</pre>
				</Card.CardContent>
			</Card.Card>
		</Tabs.TabsContent>
	</Tabs.Tabs>
</div>
