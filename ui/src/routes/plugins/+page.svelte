<script lang="ts">
	import { onMount } from 'svelte';

	import { PersephoneApi, type PluginSummary } from '$lib/api';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';

	const api = new PersephoneApi();
	let plugins = $state<PluginSummary[]>([]);
	let error = $state('');

	onMount(async () => {
		try {
			plugins = await api.listPlugins();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unable to load plugins.';
		}
	});
</script>

<div class="space-y-5">
	<div>
		<h1 class="text-2xl font-semibold tracking-normal">Plugins</h1>
		<p class="text-sm text-muted-foreground">Installed simulation capabilities.</p>
	</div>

	<Card.Card>
		<Card.CardContent class="pt-6">
			{#if error}
				<p class="text-sm text-destructive">{error}</p>
			{:else}
				<Table.Table>
					<Table.TableHeader>
						<Table.TableRow>
							<Table.TableHead>Name</Table.TableHead>
							<Table.TableHead>Version</Table.TableHead>
							<Table.TableHead>Paradigm</Table.TableHead>
						</Table.TableRow>
					</Table.TableHeader>
					<Table.TableBody>
						{#each plugins as plugin (plugin.name)}
							<Table.TableRow>
								<Table.TableCell class="font-medium">{plugin.name}</Table.TableCell>
								<Table.TableCell>{plugin.version}</Table.TableCell>
								<Table.TableCell>{plugin.paradigm}</Table.TableCell>
							</Table.TableRow>
						{/each}
					</Table.TableBody>
				</Table.Table>
			{/if}
		</Card.CardContent>
	</Card.Card>
</div>
