<script lang="ts">
	import { page } from '$app/stores';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { getDocumentDetail } from '$lib/api/documents';
	import HealthValueRow from '$lib/components/health/HealthValueRow.svelte';
	import AiInterpretationCard from '$lib/components/health/AiInterpretationCard.svelte';
	import AiFollowUpChat from '$lib/components/health/AiFollowUpChat.svelte';
	import PatternCard from '$lib/components/health/PatternCard.svelte';
	import ProcessingPipeline from '$lib/components/health/ProcessingPipeline.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { formatDate as formatDateLocalized } from '$lib/i18n/format';

	const copy = $derived(t(localeStore.locale).documents);

	const documentId = $derived($page.params.id ?? '');
	const queryClient = useQueryClient();

	const docQuery = createQuery(() => ({
		queryKey: ['document', documentId] as const,
		queryFn: () => getDocumentDetail(documentId)
	}));

	function handleProcessingComplete() {
		queryClient.invalidateQueries({ queryKey: ['document', documentId] });
		queryClient.invalidateQueries({ queryKey: ['ai_patterns'] });
	}

	function handleProcessingFailed() {
		queryClient.invalidateQueries({ queryKey: ['document', documentId] });
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
</script>

<svelte:head>
	<title>{copy.detailHeadTitle}</title>
</svelte:head>

<div class="hc-doc-detail-page">
	<a href="/documents" class="hc-doc-detail-back">{copy.detailBack}</a>

	{#if docQuery.isPending}
		<div class="hc-doc-detail-loading">
			<p>{copy.detailLoading}</p>
		</div>
	{:else if docQuery.isError}
		<div class="hc-state hc-state-error" role="alert">
			<p class="hc-state-title">{copy.detailLoadError}</p>
		</div>
	{:else if docQuery.data}
		{@const doc = docQuery.data}

		<div class="hc-doc-detail-meta">
			<h1 class="hc-doc-detail-title">{doc.filename}</h1>
			<p class="hc-doc-detail-subtitle">
				{formatDate(doc.created_at)} · {formatFileSize(doc.file_size_bytes)}
			</p>
		</div>

		{#if doc.status === 'processing' || doc.status === 'pending'}
			<ProcessingPipeline
				documentId={doc.id}
				onComplete={handleProcessingComplete}
				onFailed={handleProcessingFailed}
			/>
		{:else}
			{#if doc.health_values.length > 0}
				<section class="hc-doc-detail-values-section">
					<h2 class="hc-doc-detail-values-heading">
						{copy.detailExtractedValuesHeader} ({doc.health_values.length})
					</h2>
					<div class="hc-doc-detail-values-list">
						{#each doc.health_values as hv (hv.id)}
							<HealthValueRow {hv} documentId={doc.id} />
						{/each}
					</div>
				</section>
			{:else}
				<p class="hc-doc-detail-empty">{copy.detailNoExtractedValues}</p>
			{/if}

			{#if doc.status === 'completed' || doc.status === 'partial'}
				<AiInterpretationCard documentId={doc.id} />
				<AiFollowUpChat documentId={doc.id} />
				<PatternCard />
			{/if}
		{/if}
	{/if}
</div>
