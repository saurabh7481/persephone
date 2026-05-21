<script lang="ts">
	import { studioPrinciples, studioTokenGroups } from '$lib/studio/tokens';
	import { StudioPanel } from '$lib/components/studio';
	import { Button } from '$lib/components/ui/button';
	import * as Badge from '$lib/components/ui/badge';
</script>

<div class="grid gap-4">
	<div>
		<h1 class="text-xl font-semibold">Studio design system</h1>
		<p class="text-sm text-muted-foreground">
			Foundations for the Persephone Simulation Studio interface.
		</p>
	</div>

	<div class="grid gap-4 xl:grid-cols-[1fr_1fr]">
		<StudioPanel title="Principles" description="How the product should feel under pressure.">
			<div class="flex flex-wrap gap-2">
				{#each studioPrinciples as principle (principle)}
					<Badge.Badge variant="secondary">{principle}</Badge.Badge>
				{/each}
			</div>
		</StudioPanel>

		<StudioPanel title="Controls" description="shadcn-svelte controls with Persephone usage rules.">
			<div class="flex flex-wrap gap-2">
				<Button>Run</Button>
				<Button variant="secondary">Pause</Button>
				<Button variant="outline">Replay</Button>
				<Button variant="ghost">Inspect</Button>
			</div>
		</StudioPanel>
	</div>

	<StudioPanel title="Color tokens" description="Accessible light and dark Studio palettes.">
		<div class="grid gap-3 md:grid-cols-2">
			{#each Object.entries(studioTokenGroups) as [theme, tokens] (theme)}
				<div class="rounded-md border p-3">
					<h2 class="mb-3 text-sm font-semibold capitalize">{theme}</h2>
					<div class="grid grid-cols-2 gap-2">
						{#each Object.entries(tokens) as [name, value] (name)}
							<div class="flex items-center gap-2 text-xs">
								<span
									class="h-6 w-6 rounded border"
									style={`background: ${value}`}
									aria-hidden="true"
								></span>
								<span class="font-mono">{name}</span>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</StudioPanel>
</div>
