<script lang="ts">
	import { apiBaseUrl } from '$lib/api';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
</script>

<div class="space-y-5">
	<div>
		<h1 class="text-2xl font-semibold tracking-normal">Settings</h1>
		<p class="text-sm text-muted-foreground">Local UI connection details.</p>
	</div>

	<Card.Card>
		<Card.CardHeader>
			<Card.CardTitle>API base URL</Card.CardTitle>
			<Card.CardDescription
				>Set with `PUBLIC_PERSEPHONE_API_URL` when starting the UI.</Card.CardDescription
			>
		</Card.CardHeader>
		<Card.CardContent>
			<Input readonly value={apiBaseUrl()} />
		</Card.CardContent>
	</Card.Card>
</div>
