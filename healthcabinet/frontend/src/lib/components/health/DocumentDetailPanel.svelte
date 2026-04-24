<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { confirmDateYear, getDocumentDetail } from '$lib/api/documents';
	import type { DocumentDetail, DocumentKind, HealthValueItem } from '$lib/types/api';
	import PartialExtractionCard from './PartialExtractionCard.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { formatDate as formatDateLocalized } from '$lib/i18n/format';

	const copy = $derived(t(localeStore.locale).documents);

	// Capture whether the current server-returned error is custom (backend-supplied English)
	// so the Ukrainian UI can retranslate the generic fallback after a locale flip.
	type YearPickerErrorKey = '' | 'generic' | 'custom';

	interface Props {
		documentId: string;
		onClose: () => void;
		onDelete: (docId: string) => void;
		onKeepPartial: (docId: string) => void;
		onReupload: (docId: string) => void;
		isKeepingPartial: boolean;
		isDeleting: boolean;
	}

	const { documentId, onClose, onDelete, onKeepPartial, onReupload, isKeepingPartial, isDeleting }: Props = $props();

	const queryClient = useQueryClient();

	let showDeleteConfirm = $state(false);
	let confirmDialogRef = $state<HTMLDivElement | null>(null);

	// Year-confirmation picker state (Story 15.2 follow-up).
	const currentYear = new Date().getFullYear();
	const YEAR_OPTIONS: readonly number[] = Array.from({ length: 16 }, (_, i) => currentYear - i);
	let yearPickerOpen = $state(false);
	let yearPickerValue = $state<number>(currentYear);
	let yearPickerSaving = $state(false);
	let yearPickerErrorKey = $state<YearPickerErrorKey>('');
	let yearPickerCustomError = $state('');

	const yearPickerError = $derived.by(() => {
		if (yearPickerErrorKey === 'generic') return copy.panelSaveYearError;
		if (yearPickerErrorKey === 'custom') return yearPickerCustomError;
		return null;
	});

	const detailQuery = createQuery(() => ({
		queryKey: ['documents', documentId] as const,
		queryFn: () => getDocumentDetail(documentId),
		enabled: !!documentId
	}));

	function healthStatus(hv: HealthValueItem): { text: string; cssClass: string } {
		if (hv.reference_range_low == null || hv.reference_range_high == null) {
			return { text: '', cssClass: '' };
		}
		if (hv.value >= hv.reference_range_low && hv.value <= hv.reference_range_high) {
			return { text: copy.panelHealthStatusOptimal, cssClass: 'hc-status-optimal' };
		}
		const lowDelta = hv.reference_range_low > 0 ? (hv.reference_range_low - hv.value) / hv.reference_range_low : 0;
		const highDelta = hv.reference_range_high > 0 ? (hv.value - hv.reference_range_high) / hv.reference_range_high : 0;
		const maxDelta = Math.max(lowDelta, highDelta);
		if (maxDelta <= 0.1) return { text: copy.panelHealthStatusBorderline, cssClass: 'hc-status-borderline' };
		if (maxDelta <= 0.3) return { text: copy.panelHealthStatusConcerning, cssClass: 'hc-status-concerning' };
		return { text: copy.panelHealthStatusAction, cssClass: 'hc-status-action' };
	}

	function statusBadge(status: DocumentDetail['status']): { symbol: string; text: string; cssClass: string } {
		switch (status) {
			case 'completed':
				return { symbol: '●', text: copy.panelDocStatusCompleted, cssClass: 'hc-doc-status-completed' };
			case 'processing':
				return { symbol: '◉', text: copy.panelDocStatusProcessing, cssClass: 'hc-doc-status-processing' };
			case 'partial':
				return { symbol: '⚠', text: copy.panelDocStatusPartial, cssClass: 'hc-doc-status-partial' };
			case 'failed':
				return { symbol: '✕', text: copy.panelDocStatusFailed, cssClass: 'hc-doc-status-failed' };
			case 'pending':
				return { symbol: '○', text: copy.panelDocStatusPending, cssClass: 'hc-doc-status-pending' };
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

	const DOCUMENT_KIND_LABEL = $derived<Record<DocumentKind, string>>({
		analysis: copy.panelKindAnalysis,
		document: copy.panelKindDocument,
		unknown: copy.panelKindUnknown
	});

	type ResultDate =
		| { kind: 'single'; label: string }
		| { kind: 'range'; label: string }
		| { kind: 'needsConfirm'; partialText: string | null }
		| { kind: 'empty' };

	function resolveResultDate(detail: DocumentDetail): ResultDate {
		if (detail.needs_date_confirmation) {
			return { kind: 'needsConfirm', partialText: detail.partial_measured_at_text };
		}
		// Unique non-null day keys across all values (normalize to UTC day to avoid TZ drift).
		const uniqueDays = new Set<string>();
		let firstDate: Date | null = null;
		let lastDate: Date | null = null;
		for (const hv of detail.health_values) {
			if (!hv.measured_at) continue;
			const d = new Date(hv.measured_at);
			const dayKey = d.toISOString().slice(0, 10);
			uniqueDays.add(dayKey);
			if (firstDate === null || d < firstDate) firstDate = d;
			if (lastDate === null || d > lastDate) lastDate = d;
		}
		if (uniqueDays.size === 0) return { kind: 'empty' };
		if (uniqueDays.size === 1 && firstDate) {
			return { kind: 'single', label: formatDate(firstDate.toISOString()) };
		}
		if (firstDate && lastDate) {
			return { kind: 'range', label: `${formatDate(firstDate.toISOString())} – ${formatDate(lastDate.toISOString())}` };
		}
		return { kind: 'empty' };
	}

	function countFlagged(values: HealthValueItem[]): number {
		return values.reduce((n, v) => (v.is_flagged ? n + 1 : n), 0);
	}

	function countNeedsReview(values: HealthValueItem[]): number {
		return values.reduce((n, v) => (v.needs_review ? n + 1 : n), 0);
	}

	function openYearPicker() {
		yearPickerValue = currentYear;
		yearPickerErrorKey = '';
		yearPickerCustomError = '';
		yearPickerSaving = false;
		yearPickerOpen = true;
	}

	function cancelYearPicker() {
		yearPickerOpen = false;
		yearPickerErrorKey = '';
		yearPickerCustomError = '';
	}

	async function saveYear() {
		if (yearPickerSaving) return;
		yearPickerSaving = true;
		yearPickerErrorKey = '';
		yearPickerCustomError = '';
		try {
			const updated = await confirmDateYear(documentId, yearPickerValue);
			queryClient.setQueryData(['documents', documentId], updated);
			// Invalidate list + dashboard-dependent queries so confirmed dates refresh cached views.
			await queryClient.invalidateQueries({ queryKey: ['documents'] });
			await queryClient.invalidateQueries({ queryKey: ['health_values'] });
			await queryClient.invalidateQueries({
				queryKey: ['ai_dashboard_interpretation'],
				refetchType: 'none'
			});
			yearPickerOpen = false;
		} catch (err) {
			const apiErr = err as { detail?: string | Array<Record<string, unknown>>; title?: string };
			const detail = typeof apiErr.detail === 'string' ? apiErr.detail : null;
			const custom = detail ?? apiErr.title;
			if (custom && custom.trim().length > 0) {
				yearPickerCustomError = custom;
				yearPickerErrorKey = 'custom';
			} else {
				yearPickerErrorKey = 'generic';
			}
		} finally {
			yearPickerSaving = false;
		}
	}

	function formatFileSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			if (showDeleteConfirm) {
				showDeleteConfirm = false;
			} else {
				onClose();
			}
		}
		// Focus trap for confirmation dialog
		if (showDeleteConfirm && e.key === 'Tab' && confirmDialogRef) {
			const focusable = confirmDialogRef.querySelectorAll<HTMLElement>('button:not([disabled])');
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}

	function handleConfirmDelete() {
		onDelete(documentId);
		showDeleteConfirm = false;
		onClose();
	}

	// Auto-focus cancel button when confirm dialog opens
	$effect(() => {
		if (showDeleteConfirm && confirmDialogRef) {
			const cancelBtn = confirmDialogRef.querySelector<HTMLElement>('button');
			cancelBtn?.focus();
		}
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<section class="hc-dash-section hc-detail-inline" aria-label={copy.panelAria}>
	<!-- Close button always visible — allows dismissal during loading/error states -->
	<button
		type="button"
		class="hc-detail-close-btn"
		aria-label={copy.panelClose}
		onclick={onClose}
	>×</button>

	{#if detailQuery.isLoading}
		<div class="hc-dash-section-body hc-detail-loading">
			<p>{copy.panelLoadingDetails}</p>
		</div>
	{:else if detailQuery.isError}
		<div class="hc-dash-section-body">
			<div class="hc-detail-error" role="alert">
				<p>{copy.panelLoadDetailsError}</p>
			</div>
		</div>
	{:else if detailQuery.data}
		{@const detail = detailQuery.data}
		{@const badge = statusBadge(detail.status)}
		{@const resultDate = resolveResultDate(detail)}
		{@const flaggedCount = countFlagged(detail.health_values)}
		{@const needsReviewCount = countNeedsReview(detail.health_values)}

		<!-- Header: icon + name + action buttons -->
		<div class="hc-dash-section-header hc-detail-header">
			<span class="hc-detail-header-filename">
				<span aria-hidden="true">{fileTypeIcon(detail.file_type)}</span>
				{detail.filename}
			</span>
			<div class="hc-detail-header-actions">
				<button type="button" onclick={() => (showDeleteConfirm = true)} class="hc-detail-delete-btn">🗑 {copy.panelDeleteButton}</button>
			</div>
		</div>

		<div class="hc-dash-section-body hc-detail-body-inline">
			<!-- Left: Metadata -->
			<div class="hc-detail-meta-grid">
				<div class="hc-detail-meta-item"><span class="hc-detail-meta-label">{copy.panelMetaType}:</span> {detail.file_type === 'application/pdf' ? 'PDF' : detail.file_type.startsWith('image/') ? `${copy.panelTypeImage} (${detail.file_type.split('/')[1].toUpperCase()})` : detail.file_type}</div>
				<div class="hc-detail-meta-item"><span class="hc-detail-meta-label">{copy.panelMetaKind}:</span> {DOCUMENT_KIND_LABEL[detail.document_kind]}</div>
				<div class="hc-detail-meta-item"><span class="hc-detail-meta-label">{copy.panelMetaImported}:</span> {formatDate(detail.created_at)}</div>
				<div class="hc-detail-meta-item hc-detail-result-date">
					<span class="hc-detail-meta-label">{copy.panelMetaResultDate}:</span>
					{#if resultDate.kind === 'single' || resultDate.kind === 'range'}
						<span>{resultDate.label}</span>
					{:else if resultDate.kind === 'needsConfirm'}
						{#if !yearPickerOpen}
							<span class="hc-detail-row-warning">
								<span aria-hidden="true">⚠</span>
								{resultDate.partialText ?? copy.panelDateMissing}{resultDate.partialText ? copy.panelYearSuffix : ''}
							</span>
							<button
								type="button"
								class="hc-detail-inline-action"
								onclick={openYearPicker}
							>{copy.panelConfirmYear}</button>
						{:else}
							<span class="hc-year-picker">
								<span class="hc-detail-row-warning">
									<span aria-hidden="true">⚠</span>
									{resultDate.partialText ?? copy.panelDateMissing}
								</span>
								<label class="hc-year-picker-label">
									<span class="hc-visually-hidden">{copy.panelYearLabel}</span>
									<select
										bind:value={yearPickerValue}
										disabled={yearPickerSaving}
										aria-label={copy.panelYearLabel}
									>
										{#each YEAR_OPTIONS as year (year)}
											<option value={year}>{year}</option>
										{/each}
									</select>
								</label>
								<button
									type="button"
									onclick={saveYear}
									disabled={yearPickerSaving}
								>{yearPickerSaving ? copy.panelSaving : copy.panelSave}</button>
								<button
									type="button"
									onclick={cancelYearPicker}
									disabled={yearPickerSaving}
								>{copy.panelCancel}</button>
							</span>
							{#if yearPickerError}
								<span class="hc-detail-row-warning hc-year-picker-error" role="alert">{yearPickerError}</span>
							{/if}
						{/if}
					{:else}
						<span>—</span>
					{/if}
				</div>
				<div class="hc-detail-meta-item"><span class="hc-detail-meta-label">{copy.panelMetaSize}:</span> {formatFileSize(detail.file_size_bytes)}</div>
				<div class="hc-detail-meta-item"><span class="hc-detail-meta-label">{copy.panelMetaStatus}:</span> <span class={badge.cssClass}>{badge.symbol} {badge.text}</span></div>
				<div class="hc-detail-meta-item"><span class="hc-detail-meta-label">{copy.panelMetaValuesExtracted}:</span> {detail.health_values.length}</div>
				<div class="hc-detail-meta-item">
					<span class="hc-detail-meta-label">{copy.panelMetaFlagged}:</span>
					<span class={flaggedCount === 0 ? 'hc-detail-count-zero' : 'hc-detail-count-flagged'}>{flaggedCount}</span>
				</div>
				<div class="hc-detail-meta-item">
					<span class="hc-detail-meta-label">{copy.panelMetaNeedsReview}:</span>
					<span class={needsReviewCount === 0 ? 'hc-detail-count-zero' : 'hc-detail-count-review'}>{needsReviewCount}</span>
				</div>

				<!-- Recovery card (partial without keep_partial, or failed) -->
				{#if (detail.status === 'partial' && !detail.keep_partial) || detail.status === 'failed'}
					<PartialExtractionCard
						status={detail.status === 'failed' ? 'failed' : 'partial'}
						documentId={detail.id}
						onReupload={onReupload}
						onKeepPartial={detail.status === 'partial' ? onKeepPartial : undefined}
						{isKeepingPartial}
					/>
				{/if}
			</div>

			<!-- Right: Extracted values table -->
			{#if detail.health_values.length > 0}
				<div class="hc-detail-values-inline">
					<div class="hc-dash-section-header">{copy.detailExtractedValuesHeader}</div>
					<div class="hc-data-table">
						<table>
							<thead>
								<tr>
									<th>{copy.panelValueHeader}</th>
									<th>{copy.panelValueValue}</th>
									<th>{copy.panelValueUnit}</th>
									<th>{copy.panelValueStatus}</th>
								</tr>
							</thead>
							<tbody>
								{#each detail.health_values as hv (hv.id)}
									{@const status = healthStatus(hv)}
									<tr>
										<td>{hv.biomarker_name}</td>
										<td><strong>{hv.value}</strong></td>
										<td>{hv.unit ?? '—'}</td>
										<td class={status.cssClass}>{status.text}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{:else}
				<div class="hc-detail-values-empty">
					<p>{copy.detailNoExtractedValues}</p>
				</div>
			{/if}
		</div>
	{/if}
</section>

<!-- Delete confirmation dialog -->
{#if showDeleteConfirm && detailQuery.data}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="hc-detail-confirm-overlay"
		onclick={(e: MouseEvent) => { if (e.target === e.currentTarget) showDeleteConfirm = false; }}
		onkeydown={() => {}}
	>
		<div
			class="hc-detail-confirm hc-dash-section"
			role="alertdialog"
			aria-modal="true"
			aria-labelledby="delete-dialog-title"
			bind:this={confirmDialogRef}
		>
			<div class="hc-dash-section-header" id="delete-dialog-title">{copy.panelConfirmDeleteTitle}</div>
			<div class="hc-dash-section-body hc-detail-confirm-body">
				<p>{copy.panelConfirmDeleteBefore}</p>
				<p class="hc-detail-confirm-filename">{detailQuery.data.filename}</p>
				<p>{copy.panelConfirmDeleteAfter}</p>
				<div class="hc-detail-confirm-buttons">
					<button type="button" onclick={() => (showDeleteConfirm = false)}>{copy.panelCancel}</button>
					<button
						type="button"
						class="hc-detail-confirm-delete"
						onclick={handleConfirmDelete}
						disabled={isDeleting}
					>{isDeleting ? copy.panelConfirmDeleting : copy.panelConfirmDelete}</button>
				</div>
			</div>
		</div>
	</div>
{/if}
