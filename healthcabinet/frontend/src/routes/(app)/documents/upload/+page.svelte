<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { useQueryClient } from '@tanstack/svelte-query';
	import DocumentUploadZone from '$lib/components/health/DocumentUploadZone.svelte';
	import ProcessingPipeline from '$lib/components/health/ProcessingPipeline.svelte';
	import PartialExtractionCard from '$lib/components/health/PartialExtractionCard.svelte';
	import UploadQueuePanel from '$lib/components/health/UploadQueuePanel.svelte';
	import UploadBatchSummary from '$lib/components/health/UploadBatchSummary.svelte';
	import type { Document } from '$lib/types/api';
	import {
		handleProcessingComplete,
		handleProcessingFailure,
		handleUploadSuccess,
		type UploadState
	} from './page-state';
	import {
		applyTerminalStatus,
		createUploadQueue,
		getActiveEntry,
		getQueueStatus,
		processNextInQueue,
		validateFilesForQueue,
		type UploadQueueEntry,
		type ValidationReasonCode
	} from '$lib/upload-queue';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t, type Messages } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).upload);

	// Turn a validation reasonCode into locale-aware copy at render time so the
	// rejected-files banner re-translates when the user toggles EN/UA after a
	// rejection has already landed.
	function resolveValidationReason(
		code: ValidationReasonCode,
		upload: Messages['upload']
	): string {
		return code === 'unsupportedType' ? upload.errorUnsupportedType : upload.errorTooLarge;
	}

	const queryClient = useQueryClient();

	const retryDocumentId = $derived($page.url.searchParams.get('retryDocumentId'));
	const isRetryMode = $derived(Boolean(retryDocumentId));

	// ===== Retry (single-file) mode state — untouched from Story 2.5 flow =====
	let uploadState = $state<UploadState>('idle');
	let documentId = $state<string | null>(null);
	let uploadedFilename = $state<string | null>(null);
	let uploadedFileSize = $state<number | null>(null);

	// ===== Multi-file queue state (new for 15.4) =====
	let queue = $state<UploadQueueEntry[]>([]);
	// Rejected files carry reason *codes*, not resolved strings, so banner
	// copy retranslates on locale flip (AC 3).
	let rejectedFiles = $state<{ name: string; reasonCode: ValidationReasonCode }[]>([]);
	// Boolean flag so the auth-error banner re-derives its message on locale flip.
	let queueAuthErrorActive = $state(false);

	const queueStatus = $derived(getQueueStatus(queue));

	const sectionTitle = $derived.by(() => {
		if (isRetryMode) {
			if (uploadState === 'success') return copy.sectionRetryProcessing;
			if (uploadState === 'done') return copy.sectionRetryDone;
			if (uploadState === 'partial') return copy.sectionRetryPartial;
			if (uploadState === 'failed') return copy.sectionRetryFailed;
			return copy.sectionRetryIdle;
		}
		if (queueStatus === 'active') return copy.sectionBatchActive;
		if (queueStatus === 'summary') return copy.sectionBatchSummary;
		return copy.sectionBatchIdle;
	});

	function navigateBack(): void {
		goto('/documents');
	}

	// ===== Single-file retry flow handlers (unchanged) =====

	function onUploadSuccess(doc: Document): void {
		uploadedFilename = doc.filename;
		uploadedFileSize = doc.file_size_bytes;
		const next = handleUploadSuccess(doc);
		documentId = next.documentId;
		uploadState = next.uploadState;
	}

	function handleComplete(): void {
		const next = handleProcessingComplete(queryClient, { uploadState, documentId });
		documentId = next.documentId;
		uploadState = next.uploadState;
	}

	function handleFailed(reason: 'failed' | 'partial' | 'stream-error' = 'failed'): void {
		const next = handleProcessingFailure(queryClient, { uploadState, documentId }, reason);
		documentId = next.documentId;
		uploadState = next.uploadState;
	}

	function handleReupload(docId: string): void {
		window.location.href = `/documents/upload?retryDocumentId=${encodeURIComponent(docId)}`;
	}

	function formatFileSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	// ===== Multi-file queue handlers =====

	function setQueue(mutate: (current: UploadQueueEntry[]) => UploadQueueEntry[]): void {
		queue = mutate(queue);
	}

	function startQueueProcessing(): void {
		if (queueAuthErrorActive) return;
		processNextInQueue({
			queryClient,
			getQueue: () => queue,
			setQueue,
			uploadFailedMessage: copy.uploadFailedFallback
		});
	}

	function onActiveComplete(entryId: string): void {
		queueAuthErrorActive = false;
		applyTerminalStatus(queryClient, setQueue, entryId, 'completed');
		startQueueProcessing();
	}

	function onActiveAuthError(entryId: string): void {
		queueAuthErrorActive = true;
		// Entry error stays string (backend-passthrough compatible per AC 5);
		// the banner above reads from queueAuthErrorActive so it retranslates.
		applyTerminalStatus(queryClient, setQueue, entryId, 'failed', copy.sessionExpired);
	}

	function onActiveFailed(
		entryId: string,
		reason: 'failed' | 'partial' | 'stream-error' = 'failed'
	): void {
		queueAuthErrorActive = false;
		if (reason === 'partial') {
			applyTerminalStatus(queryClient, setQueue, entryId, 'partial');
		} else {
			applyTerminalStatus(
				queryClient,
				setQueue,
				entryId,
				'failed',
				reason === 'stream-error' ? copy.streamConnectionLost : copy.processingFailedFallback
			);
		}
		startQueueProcessing();
	}

	function onFilesSelected(files: File[]): void {
		queueAuthErrorActive = false;
		const { accepted, rejected } = validateFilesForQueue(files);
		rejectedFiles = rejected.map((r) => ({ name: r.file.name, reasonCode: r.reasonCode }));

		if (accepted.length === 0) return;

		const newEntries = createUploadQueue(accepted);
		if (queue.length === 0 || queueStatus === 'summary') {
			queue = newEntries;
		} else {
			queue = [...queue, ...newEntries];
		}

		// Only kick off processing if nothing is active right now.
		if (!getActiveEntry(queue)) startQueueProcessing();
	}

	function onRetryEntry(entryId: string): void {
		// Re-open the file picker via a hidden input. For MVP we prompt via a native
		// input click so the user can select a replacement file for this slot.
		queueAuthErrorActive = false;
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = 'image/*,application/pdf';
		input.onchange = () => {
			const replacement = input.files?.[0];
			if (!replacement) return;
			const { accepted, rejected } = validateFilesForQueue([replacement]);
			if (rejected.length > 0) {
				rejectedFiles = [
					...rejectedFiles,
					{ name: replacement.name, reasonCode: rejected[0].reasonCode }
				];
				return;
			}
			// Replace the failed entry in place with a fresh queued entry.
			queue = queue.map((e) =>
				e.id === entryId && accepted[0]
					? {
							...e,
							file: accepted[0],
							status: 'queued' as const,
							error: undefined,
							documentId: undefined
						}
					: e
			);
			if (!getActiveEntry(queue)) startQueueProcessing();
		};
		input.click();
	}

	function resetBatch(): void {
		queue = [];
		rejectedFiles = [];
		queueAuthErrorActive = false;
	}
</script>

<svelte:head>
	<title>{copy.headTitle}</title>
</svelte:head>

<div class="hc-import-page">
	<div class="hc-import-dialog hc-dash-section" role="region" aria-label={copy.pageAriaRegion}>
		<div class="hc-dash-section-header hc-import-header">
			<span class="hc-import-title">{sectionTitle}</span>
		</div>

		<div class="hc-import-body">
			{#if isRetryMode}
				<!-- ===== Single-file retry mode (Story 2.5 flow, unchanged) ===== -->
				{#if uploadState === 'idle'}
					<p class="hc-import-subtitle">{copy.subtitleRetry}</p>
					<div class="hc-import-dropzone">
						<DocumentUploadZone onSuccess={onUploadSuccess} {retryDocumentId} />
					</div>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.cancel}</button>
					</div>
				{:else if uploadState === 'success' && documentId}
					{#if uploadedFilename}
						<div class="hc-import-file-info-panel">
							<span aria-hidden="true">📄</span>
							<span class="hc-import-file-name">{uploadedFilename}</span>
							{#if uploadedFileSize}
								<span class="hc-import-file-size">({formatFileSize(uploadedFileSize)})</span>
							{/if}
						</div>
					{/if}

					<div class="hc-import-pipeline">
						<ProcessingPipeline
							{documentId}
							onComplete={handleComplete}
							onFailed={handleFailed}
						/>
					</div>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.cancel}</button>
					</div>
				{:else if uploadState === 'done'}
					<div class="hc-import-success" role="status">
						<p>{copy.successText}</p>
						<p>{copy.successSub}</p>
						<a href="/documents" class="hc-import-link">{copy.viewResults}</a>
					</div>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.close}</button>
					</div>
				{:else if uploadState === 'partial' && documentId}
					<PartialExtractionCard
						status="partial"
						{documentId}
						onReupload={handleReupload}
					/>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.close}</button>
					</div>
				{:else if uploadState === 'failed' && documentId}
					<PartialExtractionCard
						status="failed"
						{documentId}
						onReupload={handleReupload}
					/>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.close}</button>
					</div>
				{:else if uploadState === 'partial'}
					<div class="hc-import-partial" role="status">
						<p>{copy.partialBannerText}</p>
						<p>{copy.partialBannerSub}</p>
						<a href="/documents" class="hc-import-link">{copy.viewResults}</a>
					</div>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.close}</button>
					</div>
				{:else if uploadState === 'failed'}
					<div class="hc-import-error" role="alert">
						<p>{copy.errorProcessingFailed}</p>
						<a href="/documents/upload" class="hc-import-link">{copy.tryUploadAgain}</a>
					</div>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.close}</button>
					</div>
				{/if}
			{:else}
				<!-- ===== Multi-file queue mode ===== -->
				{#if queueAuthErrorActive}
					<div
						role="alert"
						aria-label={copy.authErrorAria}
						style="padding: 8px 10px; border: 1px solid var(--status-action, #e05252); background: rgba(224, 82, 82, 0.08); font-size: 12px;"
					>
						<p style="margin: 0;">{copy.sessionExpired}</p>
					</div>
				{/if}

				{#if rejectedFiles.length > 0}
					<div
						role="alert"
						aria-label={copy.rejectedFilesAria}
						style="padding: 8px 10px; border: 1px solid var(--status-action, #e05252); background: rgba(224, 82, 82, 0.08); font-size: 12px;"
					>
						<p>{copy.rejectedFilesIntro}</p>
						<ul style="margin: 4px 0 0; padding-left: 18px;">
							{#each rejectedFiles as rej (rej.name + rej.reasonCode)}
								<li>
									<strong>{rej.name}</strong> — {resolveValidationReason(rej.reasonCode, copy)}
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if queueStatus === 'idle'}
					<p class="hc-import-subtitle">{copy.subtitleBatch}</p>
					<div class="hc-import-dropzone">
						<DocumentUploadZone multiple {onFilesSelected} />
					</div>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.cancel}</button>
					</div>
				{:else if queueStatus === 'active'}
					<UploadQueuePanel
						{queue}
						{onActiveComplete}
						{onActiveAuthError}
						{onActiveFailed}
						{onRetryEntry}
					/>

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.cancelBatch}</button>
					</div>
				{:else if queueStatus === 'summary'}
					<UploadBatchSummary {queue} onStartAnother={resetBatch} />

					<div class="hc-import-actions hc-import-actions-end">
						<button type="button" onclick={navigateBack}>{copy.close}</button>
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>
