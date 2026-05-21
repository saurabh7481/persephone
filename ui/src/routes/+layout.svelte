<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { StudioShell } from '$lib/components/studio';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Persephone</title>
</svelte:head>

<StudioShell>
	{@render children()}
</StudioShell>
