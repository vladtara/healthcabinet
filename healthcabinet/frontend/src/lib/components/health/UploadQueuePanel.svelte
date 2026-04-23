<script lang="ts">
	import ProcessingPipeline from './ProcessingPipeline.svelte';
	import UploadQueueEntryRow from './UploadQueueEntryRow.svelte';
	import {
		countByStatus,
		getActiveEntry,
		type UploadQueueEntry
	} from '$lib/upload-queue';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).upload);

	interface Props {
		queue: UploadQueueEntry[];
		/** Fires when ProcessingPipeline reports completion for the active entry. */
		onActiveComplete?: (entryId: string) => void;
		/** Fires when ProcessingPipeline reports failure for the active entry. */
		onActiveFailed?: (entryId: string, reason?: 'failed' | 'partial' | 'stream-error') => void;
		/** Fires when ProcessingPipeline reports an authentication failure. */
		onActiveAuthError?: (entryId: string) => void;
		onRetryEntry?: (entryId: string) => void;
	}

	let { queue, onActiveComplete, onActiveFailed, onActiveAuthError, onRetryEntry }: Props = $props();

	const activeEntry = $derived(getActiveEntry(queue));
	const counts = $derived(countByStatus(queue));
</script>

<section aria-label={copy.queuePanelAria} style="display: flex; flex-direction: column; gap: 12px;">
	<header style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; border-bottom: 1px solid var(--surface-raised, #2a2e38); font-size: 12px;">
		<span style="font-weight: 600;">{copy.queueHeader}</span>
		<span aria-live="polite" style="color: var(--text-muted, #8a8f98);">
			{counts.completed} {copy.queueCompleteLabel} · {counts.partial} {copy.queuePartialLabel} · {counts.failed}
			{copy.queueFailedLabel} · {counts.queued + counts.uploading + counts.processing} {copy.queuePendingLabel}
		</span>
	</header>

	<ol role="list" style="list-style: none; padding: 0; margin: 0;">
		{#each queue as entry (entry.id)}
			<UploadQueueEntryRow
				{entry}
				isActive={activeEntry?.id === entry.id}
				onRetry={onRetryEntry}
			/>
		{/each}
	</ol>

	{#if activeEntry && activeEntry.documentId}
		<div
			aria-label={copy.queueActiveAria}
			style="padding: 10px; border: 1px solid var(--surface-raised, #2a2e38); background: var(--surface-raised, #1a1d24);"
		>
			<p style="margin: 0 0 8px; font-size: 12px; color: var(--text-muted, #8a8f98);">
				{copy.queueCurrentlyProcessing} {activeEntry.file.name}
			</p>
			<ProcessingPipeline
				documentId={activeEntry.documentId}
				onComplete={() => onActiveComplete?.(activeEntry.id)}
				onFailed={(reason) => onActiveFailed?.(activeEntry.id, reason)}
				onAuthError={() => onActiveAuthError?.(activeEntry.id)}
			/>
		</div>
	{:else if activeEntry}
		<div style="padding: 10px; border: 1px solid var(--surface-raised, #2a2e38); background: var(--surface-raised, #1a1d24);">
			<p style="margin: 0 0 8px; font-size: 12px; color: var(--text-muted, #8a8f98);">
				{copy.queueUploadingFile} {activeEntry.file.name}…
			</p>
		</div>
	{/if}
</section>
