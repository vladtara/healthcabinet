<script lang="ts">
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import type { QueryClient } from '@tanstack/query-core';
	import type { HealthValueItem } from '$lib/types/api';
	import HealthValueRow from './HealthValueRow.svelte';

	interface Props {
		queryClient: QueryClient;
		hv: HealthValueItem;
		documentId: string;
	}

	const { queryClient, hv, documentId }: Props = $props();
</script>

<QueryClientProvider client={queryClient}>
	<HealthValueRow {hv} {documentId} />
</QueryClientProvider>
