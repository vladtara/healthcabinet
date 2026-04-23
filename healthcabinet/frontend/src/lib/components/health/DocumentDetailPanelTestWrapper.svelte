<script lang="ts">
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import type { QueryClient } from '@tanstack/query-core';
	import DocumentDetailPanel from './DocumentDetailPanel.svelte';

	interface Props {
		queryClient: QueryClient;
		documentId: string;
		onClose: () => void;
		onDelete: (docId: string) => void;
		onKeepPartial: (docId: string) => void;
		onReupload: (docId: string) => void;
		isKeepingPartial: boolean;
		isDeleting: boolean;
	}

	const { queryClient, documentId, onClose, onDelete, onKeepPartial, onReupload, isKeepingPartial, isDeleting }: Props = $props();
</script>

<QueryClientProvider client={queryClient}>
	<DocumentDetailPanel
		{documentId}
		{onClose}
		{onDelete}
		{onKeepPartial}
		{onReupload}
		{isKeepingPartial}
		{isDeleting}
	/>
</QueryClientProvider>
