<script lang="ts">
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import type { QueryClient } from '@tanstack/query-core';
	import AiFollowUpChat from './AiFollowUpChat.svelte';

	interface Props {
		queryClient: QueryClient;
		documentId: string;
	}

	const { queryClient, documentId }: Props = $props();
</script>

<QueryClientProvider client={queryClient}>
	<AiFollowUpChat {documentId} />
</QueryClientProvider>
