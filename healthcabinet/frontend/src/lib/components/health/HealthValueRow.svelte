<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { flagHealthValue } from '$lib/api/health-values';
	import type { ApiError } from '$lib/api/client.svelte';
	import type { HealthValueItem } from '$lib/types/api';

	const { hv, documentId }: { hv: HealthValueItem; documentId: string } = $props();

	const queryClient = useQueryClient();

	let locallyFlagged = $state(false);
	let announcement = $state('');
	const isFlagged = $derived(hv.is_flagged || locallyFlagged);

	const flagMutation = createMutation(() => ({
		mutationFn: () => flagHealthValue(hv.id),
		onMutate: () => {
			announcement = '';
		},
		onSuccess: () => {
			locallyFlagged = true;
			announcement = "Thanks — we'll review this value";
			queryClient.invalidateQueries({ queryKey: ['documents', documentId] });
			queryClient.invalidateQueries({ queryKey: ['health_values'] });
		},
		onError: (error: ApiError | Error) => {
			locallyFlagged = false;
			announcement = getFlagErrorMessage(error);
		}
	}));

	const conf = $derived(confidenceLabel(hv.confidence));

	function confidenceLabel(confidence: number): { text: string; cls: string } {
		if (confidence >= 0.9) {
			return { text: 'High', cls: 'hc-health-value-row-confidence-high' };
		}
		if (confidence >= 0.7) {
			return { text: 'Medium', cls: 'hc-health-value-row-confidence-medium' };
		}
		return { text: 'Low', cls: 'hc-health-value-row-confidence-low' };
	}

	function getFlagErrorMessage(error: ApiError | Error): string {
		if ('detail' in error && typeof error.detail === 'string' && error.detail.trim().length > 0) {
			return error.detail;
		}
		return 'Unable to flag this value. Please try again.';
	}
</script>

<!-- aria-live region: polite announcement after flag action -->
<div aria-live="polite" aria-atomic="true" class="sr-only">{announcement}</div>

<div class="hc-health-value-row">
	<div class="hc-health-value-row-header">
		<span class="hc-health-value-row-name">{hv.biomarker_name}</span>
		<div class="hc-health-value-row-header-right">
			<span class="hc-health-value-row-confidence {conf.cls}">{conf.text} confidence</span>
			{#if !isFlagged}
				<button
					type="button"
					class="hc-health-value-row-flag-button"
					aria-label="Flag {hv.biomarker_name} as potentially incorrect"
					onclick={() => flagMutation.mutate()}
					disabled={flagMutation.isPending}
				>
					🚩
				</button>
			{/if}
		</div>
	</div>

	<div class="hc-health-value-row-value-line">
		<span class="hc-health-value-row-value">{hv.value}</span>
		{#if hv.unit}
			<span class="hc-health-value-row-unit">{hv.unit}</span>
		{/if}
	</div>

	{#if hv.reference_range_low !== null && hv.reference_range_high !== null}
		<p class="hc-health-value-row-reference-range">
			Ref: {hv.reference_range_low}–{hv.reference_range_high}
			{hv.unit ?? ''}
		</p>
	{/if}

	<div class="hc-health-value-row-pills">
		{#if hv.needs_review}
			<span class="hc-health-value-row-pill hc-health-value-row-pill-review">Needs review</span>
		{/if}
		{#if isFlagged}
			<span
				class="hc-health-value-row-pill hc-health-value-row-pill-flagged"
				aria-label="{hv.biomarker_name} flagged for review">Flagged</span
			>
		{/if}
	</div>
</div>
