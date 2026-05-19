<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { resolve } from '$app/paths';
	import { Activity, FlaskConical, ListTree, Plug, Settings } from '@lucide/svelte';

	let { children } = $props();

	const navItems = [
		{ href: '/runs', label: 'Runs', icon: ListTree },
		{ href: '/experiments', label: 'Experiments', icon: FlaskConical },
		{ href: '/plugins', label: 'Plugins', icon: Plug },
		{ href: '/settings', label: 'Settings', icon: Settings }
	] as const;
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Persephone</title>
</svelte:head>

<div class="min-h-screen bg-background">
	<header class="border-b bg-white">
		<div class="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3 sm:px-6">
			<a href={resolve('/runs')} class="flex items-center gap-2 font-semibold">
				<span class="grid h-8 w-8 place-items-center rounded-md bg-primary text-primary-foreground">
					<Activity size={18} />
				</span>
				<span>Persephone</span>
			</a>
			<nav class="flex flex-wrap items-center gap-1 text-sm">
				{#each navItems as item (item.href)}
					<a
						href={resolve(item.href)}
						class="flex items-center gap-2 rounded-md px-3 py-2 text-muted-foreground hover:bg-accent hover:text-foreground"
					>
						<item.icon size={16} />
						{item.label}
					</a>
				{/each}
			</nav>
		</div>
	</header>

	<main class="mx-auto max-w-7xl px-4 py-6 sm:px-6">
		{@render children()}
	</main>
</div>
