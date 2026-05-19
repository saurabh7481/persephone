<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import type { RunStatus } from '$lib/api';

	let { status }: { status: RunStatus } = $props();

	const tone = $derived(
		status === 'completed'
			? 'border-emerald-200 bg-emerald-50 text-emerald-700'
			: status === 'failed'
				? 'border-red-200 bg-red-50 text-red-700'
				: status === 'cancelled'
					? 'border-zinc-200 bg-zinc-50 text-zinc-700'
					: 'border-sky-200 bg-sky-50 text-sky-700'
	);
</script>

<Badge variant="outline" class={tone}>{status}</Badge>
