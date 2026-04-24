<script lang="ts">
	import { goto } from '$app/navigation';
	import { onDestroy } from 'svelte';
	import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
	import {
		listDocuments,
		deleteDocument,
		streamDocumentStatus,
		keepPartialResults
	} from '$lib/api/documents';
	import type { Document, DocumentDetail } from '$lib/types/api';
	import DocumentDetailPanel from '$lib/components/health/DocumentDetailPanel.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { formatDate as formatDateLocalized } from '$lib/i18n/format';

	const copy = $derived(t(localeStore.locale).documents);

	const queryClient = useQueryClient();

	const documentsQuery = createQuery(() => ({
		queryKey: ['documents'] as const,
		queryFn: listDocuments
	}));

	let selectedDocumentId = $state<string | null>(null);
	let isKeepingPartial = $state(false);

	const keepPartialMutation = createMutation(() => ({
		mutationFn: (docId: string) => keepPartialResults(docId),
		onMutate: () => {
			isKeepingPartial = true;
		},
		onSuccess: (_data: unknown, docId: string) => {
			queryClient.setQueryData(
				['documents'],
				(old: Document[] | undefined) =>
					old?.map((d: Document) => (d.id === docId ? { ...d, keep_partial: true } : d)) ?? []
			);
			queryClient.setQueryData(['documents', docId], (old: DocumentDetail | undefined) =>
				old ? { ...old, keep_partial: true } : old
			);
			queryClient.invalidateQueries({ queryKey: ['documents', docId] });
		},
		onSettled: () => {
			isKeepingPartial = false;
		}
	}));

	function handleReupload(docId: string): void {
		goto(`/documents/upload?retryDocumentId=${encodeURIComponent(docId)}`);
	}

	function handleKeepPartial(docId: string): void {
		keepPartialMutation.mutate(docId);
	}

	const deleteMutation = createMutation(() => ({
		mutationFn: (docId: string) => deleteDocument(docId),
		onSuccess: (_data: unknown, docId: string) => {
			queryClient.setQueryData(
				['documents'],
				(old: Document[] | undefined) => old?.filter((d: Document) => d.id !== docId) ?? []
			);
			queryClient.invalidateQueries({ queryKey: ['documents', docId] });
			queryClient.invalidateQueries({ queryKey: ['health_values'] });
			// Story 15.3 — rebuild dashboard AI aggregate after cascade removes AiMemory.
			queryClient.invalidateQueries({
				queryKey: ['ai_dashboard_interpretation'],
				refetchType: 'none'
			});
			selectedDocumentId = null;
		}
	}));

	function statusBadge(status: Document['status']): {
		symbol: string;
		text: string;
		cssClass: string;
	} {
		switch (status) {
			case 'completed':
				return { symbol: '●', text: copy.statusCompleted, cssClass: 'hc-doc-status-completed' };
			case 'processing':
				return { symbol: '◉', text: copy.statusProcessing, cssClass: 'hc-doc-status-processing' };
			case 'partial':
				return { symbol: '⚠', text: copy.statusPartial, cssClass: 'hc-doc-status-partial' };
			case 'failed':
				return { symbol: '✕', text: copy.statusFailed, cssClass: 'hc-doc-status-failed' };
			case 'pending':
				return { symbol: '○', text: copy.statusPending, cssClass: 'hc-doc-status-pending' };
			default:
				return { symbol: '?', text: String(status), cssClass: '' };
		}
	}

	function fileTypeIcon(fileType: string): string {
		if (fileType === 'application/pdf') return '📄';
		if (fileType.startsWith('image/')) return '🖼️';
		return '📎';
	}

	function formatDate(dateStr: string): string {
		return formatDateLocalized(dateStr, localeStore.locale, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function formatFileSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	// Track active SSE connections by document ID (AbortController per stream)
	const activeSSEConnections = new Map<string, AbortController>();

	// SSE-driven real-time updates for processing documents
	$effect(() => {
		const docs = documentsQuery.data;
		if (!docs) return;

		const processingIds = new Set(
			docs
				.filter((d: Document) => d.status === 'pending' || d.status === 'processing')
				.map((d: Document) => d.id)
		);

		// Abort connections for documents that are no longer processing
		for (const [id, controller] of activeSSEConnections) {
			if (!processingIds.has(id)) {
				controller.abort();
				activeSSEConnections.delete(id);
			}
		}

		// Open connections only for newly processing documents
		for (const docId of processingIds) {
			if (activeSSEConnections.has(docId)) continue;

			const controller = new AbortController();
			activeSSEConnections.set(docId, controller);

			let errorCount = 0;

			streamDocumentStatus(
				docId,
				controller.signal,
				(event) => {
					errorCount = 0;
					const status = event.event?.split('.').pop();
					const isTerminal = status === 'completed' || status === 'partial' || status === 'failed';
					if (isTerminal) {
						queryClient.invalidateQueries({ queryKey: ['documents'] });
						queryClient.invalidateQueries({ queryKey: ['documents', docId] });
						if (status !== 'failed') {
							queryClient.invalidateQueries({ queryKey: ['health_values'] });
							queryClient.invalidateQueries({ queryKey: ['timeline'] });
							// Story 15.3 — new persisted row may contribute to dashboard AI.
							queryClient.invalidateQueries({
								queryKey: ['ai_dashboard_interpretation'],
								refetchType: 'none'
							});
						}
						controller.abort();
						activeSSEConnections.delete(docId);
					}
				},
				(errorType) => {
					if (errorType === 'auth-error') {
						controller.abort();
						activeSSEConnections.delete(docId);
						return;
					}

					errorCount += 1;
					if (errorCount >= 3) {
						controller.abort();
						activeSSEConnections.delete(docId);
					}
				}
			);
		}
	});

	// Abort all SSE connections when the component is destroyed
	onDestroy(() => {
		for (const controller of activeSSEConnections.values()) {
			controller.abort();
		}
		activeSSEConnections.clear();
	});

	function handleDelete(docId: string) {
		deleteMutation.mutate(docId);
	}

	function closeDetail() {
		selectedDocumentId = null;
	}
</script>

<svelte:head>
	<title>{copy.headTitle}</title>
</svelte:head>

<div class="hc-doc-page">
	<div class="hc-dash-section">
		<div class="hc-dash-section-header hc-doc-page-header">
			<span>{copy.listTitle}</span>
			<a href="/documents/upload">{copy.upload}</a>
		</div>

		<div class="hc-dash-section-body">
			{#if documentsQuery.isLoading}
				<div class="hc-detail-loading">
					<p>{copy.loading}</p>
				</div>
			{:else if documentsQuery.isError}
				<div class="hc-detail-error" role="alert">
					<p>{copy.loadError}</p>
				</div>
			{:else if documentsQuery.data && documentsQuery.data.length === 0}
				<div class="hc-empty-center">
					<div class="hc-empty-icon">📋</div>
					<p class="hc-detail-meta-filename">{copy.emptyTitle}</p>
					<p class="hc-detail-meta-sub">{copy.emptySub}</p>
					<a href="/documents/upload" class="hc-doc-upload-cta">{copy.emptyUploadCta}</a>
				</div>
			{:else if documentsQuery.data}
				<div class="hc-data-table">
					<table>
						<thead>
							<tr>
								<th class="hc-doc-icon-col"><span class="sr-only">{copy.headerTypeSr}</span></th>
								<th>{copy.headerDocumentId}</th>
								<th>{copy.headerName}</th>
								<th>{copy.headerDate}</th>
								<th>{copy.headerStatus}</th>
								<th>{copy.headerSize}</th>
								<th><span class="sr-only">{copy.headerActions}</span></th>
							</tr>
						</thead>
						<tbody>
							{#each documentsQuery.data as doc (doc.id)}
								{@const badge = statusBadge(doc.status)}
								<tr
									class="hc-row-interactive"
									class:hc-doc-row-selected={selectedDocumentId === doc.id}
									aria-current={selectedDocumentId === doc.id ? 'true' : undefined}
									tabindex="0"
									onclick={() => {
										selectedDocumentId = doc.id;
									}}
									onkeydown={(e: KeyboardEvent) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											selectedDocumentId = doc.id;
										}
									}}
								>
									<td class="hc-doc-icon" aria-hidden="true">{fileTypeIcon(doc.file_type)}</td>
									<td style="font-size: 12px; color: var(--text-secondary); font-family: monospace;"
										>{doc.id.substring(0, 8)}</td
									>
									<td class="hc-doc-name">{doc.filename}</td>
									<td>{formatDate(doc.created_at)}</td>
									<td>
										<span class="hc-doc-status {badge.cssClass}">
											<span aria-hidden="true">{badge.symbol}</span>
											{badge.text}
										</span>
									</td>
									<td>{formatFileSize(doc.file_size_bytes)}</td>
									<td class="hc-doc-actions">
										<button
											type="button"
											title={copy.viewDetail}
											aria-label="{copy.viewFilenameAria} {doc.filename}"
											onclick={(e: MouseEvent) => {
												e.stopPropagation();
												selectedDocumentId = doc.id;
											}}>👁</button
										>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
	</div>

	<!-- Detail panel -->
	{#if selectedDocumentId}
		<DocumentDetailPanel
			documentId={selectedDocumentId}
			onClose={closeDetail}
			onDelete={handleDelete}
			onKeepPartial={handleKeepPartial}
			onReupload={handleReupload}
			{isKeepingPartial}
			isDeleting={deleteMutation.isPending}
		/>
	{/if}
</div>
