<script lang="ts">
	import { resolve } from '$app/paths';
	import {
		Activity,
		Boxes,
		Command,
		FlaskConical,
		GitCompareArrows,
		ListTree,
		Plug,
		Settings,
		SlidersHorizontal
	} from '@lucide/svelte';

	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { dismissToast, studioToasts } from '$lib/studio/toasts';

	let { children }: { children?: import('svelte').Snippet } = $props();
	let commandOpen = $state(false);

	const navItems = [
		{ href: '/runs', label: 'Runs', icon: ListTree },
		{ href: '/experiments', label: 'Studio', icon: FlaskConical },
		{ href: '/sweeps', label: 'Sweeps', icon: SlidersHorizontal },
		{ href: '/compare', label: 'Compare', icon: GitCompareArrows },
		{ href: '/plugins', label: 'Plugins', icon: Plug },
		{ href: '/settings', label: 'Settings', icon: Settings }
	] as const;

	function handleShellKeydown(event: KeyboardEvent) {
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
			event.preventDefault();
			commandOpen = true;
		}
		if (!event.metaKey && !event.ctrlKey && event.key.toLowerCase() === 'n') {
			const target = event.target as HTMLElement | null;
			if (target?.matches('input, textarea, select, [contenteditable="true"]')) return;
			location.href = resolve('/experiments');
		}
	}
</script>

<svelte:window onkeydown={handleShellKeydown} />

<Tooltip.TooltipProvider>
	<div class="studio-shell">
		<header class="studio-topbar">
			<a href={resolve('/runs')} class="studio-brand" aria-label="Persephone runs">
				<span class="studio-brand-mark"><Activity size={18} /></span>
				<span>
					<span class="studio-brand-name">Persephone</span>
					<span class="studio-brand-subtitle">Simulation Studio</span>
				</span>
			</a>
			<div class="studio-topbar-context" aria-label="Project context">
				<span>Local workspace</span>
				<span class="studio-context-divider"></span>
				<span>Python runtime</span>
			</div>
			<div class="studio-topbar-actions">
				<Button variant="outline" size="sm" onclick={() => (commandOpen = true)}>
					<Command size={15} />
					Command
				</Button>
				<Button href={resolve('/experiments')} size="sm">
					<FlaskConical size={15} />
					New experiment
				</Button>
			</div>
		</header>

		<aside class="studio-rail" aria-label="Primary navigation">
			{#each navItems as item (item.href)}
				<Tooltip.Tooltip>
					<Tooltip.TooltipTrigger>
						<a href={resolve(item.href)} class="studio-rail-link" aria-label={item.label}>
							<item.icon size={18} />
						</a>
					</Tooltip.TooltipTrigger>
					<Tooltip.TooltipContent side="right">{item.label}</Tooltip.TooltipContent>
				</Tooltip.Tooltip>
			{/each}
		</aside>

		<aside class="studio-context-panel" aria-label="Studio context">
			<div>
				<p class="studio-eyebrow">Workbench</p>
				<h2 class="studio-context-title">Live simulation flow</h2>
			</div>
			<nav class="studio-context-nav" aria-label="Workflow">
				<a href={resolve('/experiments')}><FlaskConical size={15} /> Create</a>
				<a href={resolve('/runs')}><Activity size={15} /> Playback</a>
				<a href={resolve('/compare')}><GitCompareArrows size={15} /> Analyze</a>
				<a href={resolve('/plugins')}><Boxes size={15} /> Extend</a>
			</nav>
		</aside>

		<main class="studio-main" aria-label="Studio workspace">
			{@render children?.()}
		</main>
	</div>

	<Dialog.Dialog bind:open={commandOpen}>
		<Dialog.DialogContent>
			<Dialog.DialogHeader>
				<Dialog.DialogTitle>Command palette</Dialog.DialogTitle>
				<Dialog.DialogDescription>Jump between Studio workflows.</Dialog.DialogDescription>
			</Dialog.DialogHeader>
			<div class="grid gap-2">
				{#each navItems as item (item.href)}
					<a
						class="studio-command-item"
						href={resolve(item.href)}
						onclick={() => (commandOpen = false)}
					>
						<item.icon size={16} />
						<span>{item.label}</span>
					</a>
				{/each}
			</div>
			<Dialog.DialogFooter>
				<p class="text-xs text-muted-foreground">
					Shortcut: Cmd/Ctrl+K. Press N for a new experiment.
				</p>
			</Dialog.DialogFooter>
		</Dialog.DialogContent>
	</Dialog.Dialog>

	<div class="studio-toast-region" aria-live="polite" aria-label="Notifications">
		{#each $studioToasts as toast (toast.id)}
			<button
				type="button"
				class="studio-toast"
				data-tone={toast.tone ?? 'default'}
				onclick={() => dismissToast(toast.id)}
			>
				<strong>{toast.title}</strong>
				{#if toast.description}
					<span>{toast.description}</span>
				{/if}
			</button>
		{/each}
	</div>
</Tooltip.TooltipProvider>
