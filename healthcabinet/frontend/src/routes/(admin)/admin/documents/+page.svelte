<script lang="ts">
	import { goto } from '$app/navigation';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { getErrorQueue } from '$lib/api/admin';
	import { DataTable, type Column } from '$lib/components/ui/data-table';

	const queryClient = useQueryClient();

	const queueQuery = createQuery(() => ({
		queryKey: ['admin', 'queue'],
		queryFn: getErrorQueue,
		refetchOnWindowFocus: false,
		refetchOnReconnect: false
	}));

	function handleRefresh() {
		queryClient.invalidateQueries({ queryKey: ['admin', 'queue'] });
	}

	function truncateId(id: string): string {
		return id.slice(0, 8) + '…';
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function getFlagReason(flaggedCount: number): string {
		return flaggedCount > 0 ? 'User-flagged' : '—';
	}

	const columns: Column[] = [
		{ key: 'document_id', label: 'Document ID', sortable: true },
		{ key: 'user_id', label: 'User ID', sortable: true },
		{ key: 'filename', label: 'Filename', sortable: true },
		{ key: 'upload_date', label: 'Upload Date', sortable: true },
		{ key: 'status', label: 'Status', sortable: true },
		{ key: 'value_count', label: 'Values', sortable: true, align: 'center' },
		{ key: 'low_confidence_count', label: 'Low Conf.', sortable: true, align: 'center' },
		{ key: 'flagged_count', label: 'Flagged', sortable: true, align: 'center' },
		{ key: 'flag_reason', label: 'Flag Reason' }
	];

	let rows = $derived(
		(queueQuery.data?.items ?? []).map((item) => ({
			document_id: item.document_id,
			user_id: item.user_id,
			filename: item.filename,
			upload_date: item.upload_date,
			status: item.status,
			value_count: item.value_count,
			low_confidence_count: item.low_confidence_count,
			flagged_count: item.flagged_count,
			flag_reason: getFlagReason(item.flagged_count)
		}))
	);

	function handleRowClick(row: Record<string, unknown>) {
		const id = row.document_id;
		if (typeof id === 'string') {
			goto(`/admin/documents/${id}`);
		}
	}
</script>

<div class="hc-admin-queue-page">
	<header class="hc-admin-queue-header">
		<div>
			<h1 class="hc-admin-queue-title">Extraction Error Queue</h1>
			<p class="hc-admin-queue-subtitle">Documents with extraction problems requiring review</p>
		</div>
		<button type="button" class="btn-standard" onclick={handleRefresh} aria-label="Refresh queue">
			Refresh
		</button>
	</header>

	{#if queueQuery.isPending}
		<div class="hc-admin-queue-skeleton" role="status" aria-label="Loading queue">
			{#each Array(3) as _}
				<div class="hc-admin-queue-skeleton-row"></div>
			{/each}
		</div>
	{:else if queueQuery.isError}
		<div class="hc-state hc-state-error">
			<div role="alert">
				<p class="hc-state-title">Unable to load extraction error queue.</p>
				<p>Try refreshing the page or contact support if the issue persists.</p>
			</div>
			<button
				type="button"
				class="btn-standard"
				onclick={handleRefresh}
				aria-label="Retry loading extraction error queue"
			>
				Try again
			</button>
		</div>
	{:else if queueQuery.data}
		{@const data = queueQuery.data}
		{#if data.items.length === 0}
			<div class="hc-admin-queue-empty-panel">
				<div class="hc-state hc-state-empty">
					<p class="hc-state-title">No documents requiring review</p>
					<p>All documents have been processed successfully or no values need correction.</p>
				</div>
			</div>
		{:else}
			<DataTable {columns} {rows} onRowClick={handleRowClick}>
				{#snippet children(row, col)}
					{#if col.key === 'document_id' || col.key === 'user_id'}
						<span class="hc-admin-correction-value-cell">{truncateId(String(row[col.key]))}</span>
					{:else if col.key === 'upload_date'}
						{formatDate(String(row.upload_date))}
					{:else if col.key === 'status'}
						{#if row.status === 'failed'}
							<span class="hc-badge hc-badge-danger">Failed</span>
						{:else if row.status === 'partial'}
							<span class="hc-badge hc-badge-warning">Partial</span>
						{:else}
							<span class="hc-badge hc-badge-default">{row.status}</span>
						{/if}
					{:else if col.key === 'value_count'}
						<span class="hc-admin-queue-count-cell">{row.value_count}</span>
					{:else if col.key === 'low_confidence_count'}
						{@const count = row.low_confidence_count as number}
						<span
							class="hc-admin-queue-count-cell {count > 0 ? 'hc-admin-queue-count-concerning' : ''}"
						>
							{count}
						</span>
					{:else if col.key === 'flagged_count'}
						{@const count = row.flagged_count as number}
						<span
							class="hc-admin-queue-count-cell {count > 0 ? 'hc-admin-queue-count-action' : ''}"
						>
							{count}
						</span>
					{:else if col.key === 'flag_reason'}
						{@const flagged = (row.flagged_count as number) > 0}
						<span class={flagged ? 'hc-admin-queue-count-action' : ''}>{row.flag_reason}</span>
					{:else}
						{row[col.key] ?? ''}
					{/if}
				{/snippet}
			</DataTable>
			<p class="hc-admin-queue-footer-count">
				Showing {data.items.length} document{data.items.length !== 1 ? 's' : ''} requiring review
			</p>
		{/if}
	{/if}
</div>
