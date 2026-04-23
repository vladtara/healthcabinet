<script lang="ts">
	import { uploadDocument, reuploadDocument } from '$lib/api/documents';
	import type { Document } from '$lib/types/api';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).upload);

	const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB
	const ACCEPTED_TYPES = ['image/', 'application/pdf'];

	type UploadState = 'idle' | 'dragging' | 'uploading' | 'success' | 'error';
	type ErrorKey = '' | 'unsupported-type' | 'too-large' | 'upload-failed' | 'single-file-only';

	let uploadState = $state<UploadState>('idle');
	let file = $state<File | null>(null);
	let errorKey = $state<ErrorKey>('');
	let fileInput = $state<HTMLInputElement | null>(null);

	const errorMessage = $derived.by(() => {
		switch (errorKey) {
			case 'unsupported-type':
				return copy.errorUnsupportedType;
			case 'too-large':
				return copy.errorTooLarge;
			case 'upload-failed':
				return copy.errorUploadFailed;
			case 'single-file-only':
				return copy.errorSingleFileOnly;
			default:
				return '';
		}
	});

	interface Props {
		/** Single-file mode callback. Fires once the upload call resolves. */
		onSuccess?: (doc: Document) => void;
		/** When set, the upload targets an existing document slot instead of creating a new row. */
		retryDocumentId?: string | null;
		/**
		 * When true, the zone accepts multiple files and surfaces them to `onFilesSelected`
		 * instead of auto-uploading. The parent (queue-aware page) drives upload per entry.
		 */
		multiple?: boolean;
		/**
		 * Multi-file mode handler. Receives every selected / dropped file (already
		 * filtered by the browser's `accept` attribute). No validation is performed
		 * inside this component in multi-file mode — callers must validate before
		 * enqueuing.
		 */
		onFilesSelected?: (files: File[]) => void;
	}

	let {
		onSuccess,
		retryDocumentId = null,
		multiple = false,
		onFilesSelected
	}: Props = $props();

	function isAcceptedType(f: File): boolean {
		return ACCEPTED_TYPES.some((t) => f.type.startsWith(t));
	}

	async function startUpload(selectedFile: File): Promise<void> {
		if (!isAcceptedType(selectedFile)) {
			errorKey = 'unsupported-type';
			uploadState = 'error';
			return;
		}

		if (selectedFile.size > MAX_FILE_SIZE) {
			errorKey = 'too-large';
			uploadState = 'error';
			return;
		}

		file = selectedFile; // Preserve for retry (AC #5)
		uploadState = 'uploading';
		errorKey = '';

		try {
			const doc = retryDocumentId
				? await reuploadDocument(retryDocumentId, selectedFile)
				: await uploadDocument(selectedFile);
			uploadState = 'success';
			onSuccess?.(doc);
		} catch {
			uploadState = 'error';
			errorKey = 'upload-failed';
		}
	}

	async function retry(): Promise<void> {
		if (!file) return;
		await startUpload(file);
	}

	function onDragOver(e: DragEvent): void {
		e.preventDefault();
		uploadState = 'dragging';
	}

	function onDragLeave(): void {
		if (uploadState === 'dragging') uploadState = 'idle';
	}

	async function onDrop(e: DragEvent): Promise<void> {
		e.preventDefault();
		const dropped = e.dataTransfer?.files;
		if (!dropped || dropped.length === 0) {
			uploadState = 'idle';
			return;
		}

		if (multiple) {
			onFilesSelected?.(Array.from(dropped));
			uploadState = 'idle';
			return;
		}

		if (dropped.length > 1) {
			file = null;
			errorKey = 'single-file-only';
			uploadState = 'error';
			return;
		}

		await startUpload(dropped[0]);
	}

	async function onFileChange(e: Event): Promise<void> {
		const input = e.currentTarget as HTMLInputElement;
		const files = input.files;
		if (!files || files.length === 0) return;

		if (multiple) {
			onFilesSelected?.(Array.from(files));
			// Reset so picking the same files again still fires change.
			input.value = '';
			return;
		}

		await startUpload(files[0]);
	}

	function handleZoneActivate(): void {
		fileInput?.click();
	}

	function handleBrowseClick(e: MouseEvent): void {
		e.stopPropagation();
		fileInput?.click();
	}

	function onKeyDown(e: KeyboardEvent): void {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleZoneActivate();
		}
	}

	let isDragging = $derived(uploadState === 'dragging');
	let isUploading = $derived(uploadState === 'uploading');
	let isSuccess = $derived(uploadState === 'success');
	let isError = $derived(uploadState === 'error');
</script>

<div
	role="button"
	tabindex="0"
	class="hc-upload-zone"
	class:hc-upload-zone-dragging={isDragging}
	class:hc-upload-zone-error={isError}
	class:hc-upload-zone-success={isSuccess}
	onclick={handleZoneActivate}
	ondragover={onDragOver}
	ondragleave={onDragLeave}
	ondrop={onDrop}
	onkeydown={onKeyDown}
	aria-label={multiple ? copy.zoneAriaMulti : copy.zoneAriaSingle}
	aria-busy={isUploading}
>
	<!-- Accessibility: announces drag state and upload state to screen readers -->
	<div aria-live="polite" class="sr-only">
		{#if isDragging}{copy.zoneDropToUpload}{/if}
		{#if isSuccess}{copy.zoneUploadComplete}{/if}
		{#if isError && errorMessage}{errorMessage}{/if}
	</div>

	{#if isUploading}
		<div class="hc-upload-zone-content">
			<div class="hc-upload-zone-spinner" aria-hidden="true"></div>
			<p class="hc-upload-zone-filename">{file?.name}</p>
			<p class="hc-upload-zone-hint">{copy.zoneUploading}</p>
		</div>
	{:else if isSuccess}
		<div class="hc-upload-zone-content">
			<p class="hc-upload-zone-success-text">{copy.zoneUploadComplete}</p>
		</div>
	{:else if isError}
		<div class="hc-upload-zone-content">
			<p class="hc-upload-zone-error-text" role="alert">{errorMessage}</p>
		</div>
	{:else}
		<div class="hc-upload-zone-content">
			<div class="hc-upload-zone-icon" aria-hidden="true">📄</div>
			<p class="hc-upload-zone-text">
				{multiple ? copy.zoneDragMulti : copy.zoneDragSingle}
			</p>
			<p class="hc-upload-zone-divider">{copy.zoneDivider}</p>
		</div>
	{/if}
</div>

<!-- Interactive elements outside role="button" to avoid nested-interactive axe violation. -->
{#if !isUploading && !isSuccess && !isError}
	<div class="hc-upload-zone-below">
		<button type="button" class="hc-upload-zone-browse" onclick={handleBrowseClick}>{copy.zoneBrowse}</button>
		<div class="hc-upload-zone-formats">
			<span class="hc-upload-zone-badge">📄 PDF</span>
			<span class="hc-upload-zone-badge">🖼️ JPG</span>
			<span class="hc-upload-zone-badge">🖼️ PNG</span>
			<span class="hc-upload-zone-maxsize">{copy.zoneMaxSize}</span>
		</div>
	</div>
{/if}

<input
	id="file-input"
	bind:this={fileInput}
	type="file"
	accept="image/*,application/pdf"
	{multiple}
	class="sr-only"
	onchange={onFileChange}
	aria-hidden="true"
	tabindex="-1"
/>

{#if isError && file}
	<button
		type="button"
		class="hc-upload-zone-retry"
		onclick={retry}
	>
		{copy.zoneRetry}
	</button>
{/if}
