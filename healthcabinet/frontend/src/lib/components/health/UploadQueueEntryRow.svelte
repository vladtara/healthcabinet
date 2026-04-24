<script lang="ts">
	import type { UploadQueueEntry, UploadEntryStatus } from '$lib/upload-queue';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).upload);

	interface Props {
		entry: UploadQueueEntry;
		isActive: boolean;
		/** Fires when the user asks to retry this entry (for failed rows). */
		onRetry?: (entryId: string) => void;
	}

	let { entry, isActive, onRetry }: Props = $props();

	const STATUS_LABELS = $derived<Record<UploadEntryStatus, string>>({
		queued: copy.entryStatusQueued,
		uploading: copy.entryStatusUploading,
		processing: copy.entryStatusProcessing,
		completed: copy.entryStatusComplete,
		partial: copy.entryStatusPartial,
		failed: copy.entryStatusFailed
	});

	function mapStatusToStage(status: UploadEntryStatus): string {
		if (status === 'completed') return 'done';
		if (status === 'uploading' || status === 'processing') return 'active';
		if (status === 'failed') return 'error';
		if (status === 'partial') return 'active';
		return 'pending';
	}

	function formatFileSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	const statusLabel = $derived(STATUS_LABELS[entry.status]);
	const stageToken = $derived(mapStatusToStage(entry.status));
	const statusClass = $derived(
		entry.status === 'partial' ? 'hc-badge hc-badge-warning' : `hc-pipeline-stage-${stageToken}`
	);
	const statusStyle = $derived(
		entry.status === 'partial'
			? 'grid-row: 1; font-size: 11px;'
			: 'grid-row: 1; padding: 2px 6px; font-size: 11px; border: 1px solid var(--surface-raised, #2a2e38); border-radius: 2px;'
	);
	const showResultLink = $derived(
		(entry.status === 'completed' || entry.status === 'partial') && Boolean(entry.documentId)
	);
	const showRetryAction = $derived(entry.status === 'failed');
</script>

<li
	class="hc-queue-row hc-queue-row-{entry.status}"
	class:hc-queue-row-active={isActive}
	aria-current={isActive ? 'step' : undefined}
	style="display: grid; grid-template-columns: auto 1fr auto auto; grid-template-rows: auto auto; grid-column-gap: 10px; align-items: center; padding: 8px 10px; border-bottom: 1px solid var(--surface-raised, #2a2e38); background: {isActive
		? 'var(--surface-active, rgba(79, 110, 247, 0.08))'
		: 'transparent'};"
>
	<span aria-hidden="true" style="font-size: 18px; grid-row: 1;">📄</span>
	<div style="grid-row: 1; min-width: 0;">
		<p
			title={entry.file.name}
			style="margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500;"
		>
			{entry.file.name}
		</p>
		<p style="margin: 0; font-size: 11px; color: var(--text-muted, #8a8f98);">
			{formatFileSize(entry.file.size)}
		</p>
	</div>
	<span class={statusClass} style={statusStyle}>
		{statusLabel}
	</span>
	<div style="grid-row: 1; display: flex; gap: 6px;">
		{#if showResultLink && entry.documentId}
			<a
				href={`/documents/${entry.documentId}`}
				style="text-decoration: underline; font-size: 12px;">{copy.entryViewResult}</a
			>
		{/if}
		{#if showRetryAction}
			<button type="button" onclick={() => onRetry?.(entry.id)} style="font-size: 12px;">
				{copy.entryRetryThisFile}
			</button>
		{/if}
	</div>
	{#if entry.status === 'failed' && entry.error}
		<p
			role="alert"
			style="grid-column: 1 / -1; grid-row: 2; margin: 4px 0 0; font-size: 11px; color: var(--status-action, #e05252);"
		>
			{entry.error}
		</p>
	{/if}
</li>
