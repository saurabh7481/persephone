<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs';

	let {
		tabs,
		activeTab = $bindable('artifacts'),
		children
	}: {
		tabs: Array<{ value: string; label: string }>;
		activeTab?: string;
		children?: import('svelte').Snippet<[string]>;
	} = $props();
</script>

<Tabs.Tabs bind:value={activeTab} class="space-y-4">
	<Tabs.TabsList>
		{#each tabs as tab (tab.value)}
			<Tabs.TabsTrigger value={tab.value}>{tab.label}</Tabs.TabsTrigger>
		{/each}
	</Tabs.TabsList>

	{#each tabs as tab (tab.value)}
		<Tabs.TabsContent value={tab.value}>
			{#if activeTab === tab.value}
				{@render children?.(tab.value)}
			{/if}
		</Tabs.TabsContent>
	{/each}
</Tabs.Tabs>
