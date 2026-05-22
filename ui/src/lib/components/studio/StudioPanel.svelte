<script lang="ts">
	import { cn } from '$lib/utils';

	let {
		title,
		description,
		class: className = '',
		children
	}: {
		title?: string;
		description?: string;
		class?: string;
		children?: import('svelte').Snippet;
	} = $props();
</script>

<section class={cn('studio-panel min-w-0', className)}>
	{#if title || description}
		<header class="studio-panel-header">
			{#if title}
				<h2 class="studio-panel-title">{title}</h2>
			{/if}
			{#if description}
				<p class="studio-panel-description">{description}</p>
			{/if}
		</header>
	{/if}
	<div class="studio-panel-body min-w-0">
		{@render children?.()}
	</div>
</section>
