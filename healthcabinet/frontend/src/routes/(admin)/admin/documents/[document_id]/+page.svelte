<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { untrack } from 'svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { getDocumentForCorrection, submitCorrection } from '$lib/api/admin';
	import type { CorrectionRequest } from '$lib/types/api';

	const queryClient = useQueryClient();

	const documentId = $derived.by(() => {
		const id = $page.params.document_id;
		return typeof id === 'string' && id.length > 0 ? id : null;
	});

	// Story 5.3: Support health_value_id query param for scroll-to-row from flagged reports
	const highlightValueId = $derived($page.url.searchParams.get('health_value_id'));

	const detailQuery = createQuery(() => {
		const id = documentId;
		return {
			queryKey: ['admin', 'queue', id],
			queryFn: () => {
				if (!id) {
					throw new Error('Missing document ID');
				}
				return getDocumentForCorrection(id);
			},
			enabled: id !== null
		};
	});

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Per-value correction form state
	interface CorrectionFormState {
		healthValueId: string;
		newValue: string;
		reason: string;
	}

	let correctionStates = $state<Record<string, CorrectionFormState>>({});
	let submitting = $state<Record<string, boolean>>({});
	let submitSuccess = $state<Record<string, boolean>>({});
	let submitError = $state<Record<string, string>>({});
	let hasScrolledToHighlight = $state(false);

	// Initialize form states when document data loads
	$effect(() => {
		const values = detailQuery.data?.values;
		if (values) {
			// Use untrack to avoid infinite recursion - we only depend on detailQuery.data, not correctionStates
			untrack(() => {
				for (const value of values) {
					if (!correctionStates[value.id]) {
						correctionStates[value.id] = { healthValueId: value.id, newValue: '', reason: '' };
					}
				}
			});
		}
	});

	// Story 5.3: Scroll to highlighted row when data loads (once only)
	$effect(() => {
		if (highlightValueId && detailQuery.data && !hasScrolledToHighlight) {
			untrack(() => {
				hasScrolledToHighlight = true;
				requestAnimationFrame(() => {
					const row = document.getElementById(`hv-row-${highlightValueId}`);
					if (row && typeof row.scrollIntoView === 'function') {
						row.scrollIntoView({ behavior: 'smooth', block: 'center' });
					}
				});
			});
		}
	});

	function isFormValid(state: CorrectionFormState): boolean {
		return state.reason.trim().length > 0 && !isNaN(parseFloat(state.newValue));
	}

	async function handleSubmit(healthValueId: string) {
		const id = documentId;
		const state = correctionStates[healthValueId];
		if (!id || !state) return;

		const newValueNum = parseFloat(state.newValue);
		if (!isFormValid(state)) return;

		submitting[healthValueId] = true;
		submitError[healthValueId] = '';
		submitSuccess[healthValueId] = false;

		try {
			const request: CorrectionRequest = {
				new_value: newValueNum,
				reason: state.reason.trim()
			};
			await submitCorrection(id, healthValueId, request);
			submitSuccess[healthValueId] = true;
			correctionStates[healthValueId] = { healthValueId, newValue: '', reason: '' };
			queryClient.invalidateQueries({ queryKey: ['admin', 'queue'] });
			queryClient.invalidateQueries({ queryKey: ['admin', 'queue', id] });
		} catch (err: unknown) {
			submitError[healthValueId] = err instanceof Error ? err.message : 'Submission failed';
		} finally {
			submitting[healthValueId] = false;
		}
	}
</script>

<div class="hc-admin-correction-page">
	<div class="hc-admin-correction-back-row">
		<button
			type="button"
			class="btn-standard"
			onclick={() => goto('/admin/documents')}
			aria-label="Back to extraction error queue"
		>
			← Back to Error Queue
		</button>
	</div>

	<header class="hc-admin-correction-header">
		<h1 class="hc-admin-correction-title">Document Correction</h1>
		<p class="hc-admin-correction-subtitle">Review and correct extracted health values</p>
	</header>

	{#if detailQuery.isPending}
		<div class="hc-admin-correction-skeleton" role="status" aria-label="Loading document">
			{#each Array(3) as _}
				<div class="hc-admin-correction-skeleton-row"></div>
			{/each}
		</div>
	{:else if detailQuery.isError}
		<div class="hc-state hc-state-error" role="alert">
			<p class="hc-state-title">Unable to load document details.</p>
			<p>The document may not exist or you may not have access.</p>
		</div>
	{:else if detailQuery.data}
		{@const doc = detailQuery.data}
		<fieldset class="hc-fieldset">
			<legend>Document</legend>
			<dl class="hc-admin-correction-meta-grid">
				<div>
					<dt>Filename</dt>
					<dd>{doc.filename}</dd>
				</div>
				<div>
					<dt>Status</dt>
					<dd>
						{#if doc.status === 'failed'}
							<span class="hc-badge hc-badge-danger">Failed</span>
						{:else if doc.status === 'partial'}
							<span class="hc-badge hc-badge-warning">Partial</span>
						{:else}
							<span class="hc-badge hc-badge-default">{doc.status}</span>
						{/if}
					</dd>
				</div>
				<div>
					<dt>User ID</dt>
					<dd class="hc-admin-correction-meta-mono">{doc.user_id}</dd>
				</div>
				<div>
					<dt>Upload Date</dt>
					<dd>{formatDate(doc.upload_date)}</dd>
				</div>
			</dl>
		</fieldset>

		<div class="hc-admin-correction-table">
			<table>
				<thead>
					<tr>
						<th>Biomarker</th>
						<th class="hc-admin-correction-align-right">Value</th>
						<th class="hc-admin-correction-align-center">Confidence</th>
						<th class="hc-admin-correction-align-center">Flagged</th>
						<th class="hc-admin-correction-align-center">Reference Range</th>
						<th>Correction</th>
					</tr>
				</thead>
				<tbody>
					{#each doc.values as value (value.id)}
						{@const state = correctionStates[value.id]}
						{@const isValid = state ? isFormValid(state) : false}
						{@const success = submitSuccess[value.id]}
						{@const error = submitError[value.id]}
						{@const isSubmitting = submitting[value.id]}
						{@const isHighlighted = highlightValueId === value.id}
						{@const valueInputId = `correction-value-${value.id}`}
						{@const reasonInputId = `correction-reason-${value.id}`}
						<tr
							id="hv-row-{value.id}"
							class={isHighlighted ? 'hc-admin-correction-row-highlight' : undefined}
						>
							<td>
								<p class="hc-admin-correction-biomarker-name">{value.biomarker_name}</p>
								<p class="hc-admin-correction-biomarker-canonical">
									{value.canonical_biomarker_name}
								</p>
							</td>
							<td class="hc-admin-correction-value-cell">
								{value.value}
								{value.unit ?? ''}
							</td>
							<td class="hc-admin-correction-align-center">
								{#if value.confidence < 0.7}
									<span class="hc-badge hc-badge-warning">
										{(value.confidence * 100).toFixed(0)}%
									</span>
								{:else}
									<span class="hc-admin-correction-confidence-ok">
										{(value.confidence * 100).toFixed(0)}%
									</span>
								{/if}
							</td>
							<td class="hc-admin-correction-align-center">
								{#if value.is_flagged}
									<span class="hc-badge hc-badge-danger">User-flagged</span>
								{:else}
									<span class="hc-admin-correction-no-flag">—</span>
								{/if}
							</td>
							<td class="hc-admin-correction-range-cell">
								{#if value.reference_range_low != null && value.reference_range_high != null}
									{value.reference_range_low}–{value.reference_range_high}
									{value.unit ?? ''}
								{:else}
									—
								{/if}
							</td>
							<td>
								{#if success}
									<div class="hc-admin-correction-success">
										<span aria-hidden="true">✓</span>
										<span>Corrected</span>
									</div>
								{:else if state}
									<div class="hc-admin-correction-form">
										<div class="hc-admin-correction-form-row">
											<div class="hc-admin-correction-form-field">
												<label class="hc-admin-correction-input-label" for={valueInputId}>
													New value for {value.biomarker_name}
												</label>
												<input
													id={valueInputId}
													type="number"
													step="any"
													class="hc-input hc-admin-correction-input-value"
													placeholder="New value"
													aria-label={`New value for ${value.biomarker_name}`}
													bind:value={state.newValue}
												/>
											</div>
											<div class="hc-admin-correction-form-field">
												<label class="hc-admin-correction-input-label" for={reasonInputId}>
													Correction reason for {value.biomarker_name}
												</label>
												<input
													id={reasonInputId}
													type="text"
													class="hc-input hc-admin-correction-input-reason"
													placeholder="Reason (required)"
													aria-label={`Correction reason for ${value.biomarker_name}`}
													bind:value={state.reason}
												/>
											</div>
										</div>
										{#if error}
											<p class="hc-admin-correction-field-error" role="alert">{error}</p>
										{/if}
										<button
											type="button"
											class="btn-primary"
											onclick={() => handleSubmit(value.id)}
											disabled={!isValid || isSubmitting}
										>
											{isSubmitting ? 'Saving…' : 'Submit Correction'}
										</button>
									</div>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
