<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { getDocumentInterpretation } from '$lib/api/ai';
	import type { ApiError } from '$lib/api/client.svelte';
	import type { ValueReasoning } from '$lib/api/ai';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).aiClinicalNote);

	interface Props {
		documentId: string;
	}

	let { documentId }: Props = $props();
	let showReasoning = $state(false);
	let reasoningAnnouncementVisible = $state(false);

	// Announcement text is derived so it retranslates on locale flip.
	const reasoningAnnouncement = $derived(
		reasoningAnnouncementVisible ? copy.reasoningShownAnnouncement : ''
	);

	// Reset disclosure state whenever the user navigates to a different document
	$effect(() => {
		documentId; // reactive dependency — re-runs on every documentId change
		showReasoning = false;
		reasoningAnnouncementVisible = false;
	});

	const interpretationQuery = createQuery(() => ({
		queryKey: ['ai_interpretation', documentId] as const,
		queryFn: () => getDocumentInterpretation(documentId),
		retry: false // Don't retry 404s (interpretation may not exist yet)
	}));

	function is404(error: unknown): boolean {
		return (error as ApiError)?.status === 404;
	}

	function statusLabel(status: string): string {
		switch (status) {
			case 'normal':
				return copy.statusNormal;
			case 'high':
				return copy.statusHigh;
			case 'low':
				return copy.statusLow;
			default:
				return copy.statusUnknown;
		}
	}

	function statusClass(status: string): string {
		switch (status) {
			case 'normal':
				return 'text-[#2E8B57]';
			case 'high':
				return 'text-[#CC3333]';
			case 'low':
				return 'text-[#E07020]';
			default:
				return 'text-muted-foreground';
		}
	}

	function valueKey(value: ValueReasoning, index: number): string {
		return `${value.name}-${value.value}-${value.unit ?? 'unitless'}-${index}`;
	}

	function flagKey(flag: string, index: number): string {
		return `${flag}-${index}`;
	}

	function toggleReasoning(): void {
		const isOpening = !showReasoning;
		showReasoning = isOpening;
		reasoningAnnouncementVisible = isOpening;
	}
</script>

<!-- Reasoning expansion announcer must live outside the outer atomic live region so
     that toggling the panel does not re-announce the entire card to screen readers. -->
<p class="sr-only" aria-live="polite" aria-atomic="true">{reasoningAnnouncement}</p>

<!--
  The aria-live wrapper is always present in the DOM so that screen readers
  register the live region before interpretation content is injected into it.
  WCAG requires the live region to exist before its content changes.
-->
<div aria-live="polite" aria-atomic="true">
	{#if interpretationQuery.data}
		<section
			aria-label={copy.cardAria}
			class="border-l-4 border-l-[#3366FF] bg-card/50 rounded-md p-4"
		>
			<h3 class="text-base font-semibold mb-3 text-foreground">{copy.cardHeader}</h3>
			<div class="text-[15px] leading-relaxed text-foreground mb-4">
				{interpretationQuery.data.interpretation}
			</div>
			{#if interpretationQuery.data.reasoning}
				<button
					type="button"
					class="mt-3 text-[13px] text-[#3366FF] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3366FF]"
					aria-expanded={showReasoning}
					aria-controls="reasoning-panel"
					onclick={toggleReasoning}
				>
					{showReasoning ? copy.reasoningHide : copy.reasoningShow}
				</button>

				<div id="reasoning-panel" class="mt-3" class:hidden={!showReasoning}>
					{#if showReasoning}
						{@const reasoning = interpretationQuery.data.reasoning}

						{#if reasoning.values_referenced.length > 0}
							<table class="mb-3 w-full border-collapse text-[13px]">
								<caption class="sr-only">{copy.reasoningTableCaption}</caption>
								<thead>
									<tr class="border-b border-border text-left text-muted-foreground">
										<th class="pb-1 pr-3 font-medium">{copy.biomarkerHeader}</th>
										<th class="pb-1 pr-3 font-medium">{copy.valueHeader}</th>
										<th class="pb-1 pr-3 font-medium">{copy.referenceRangeHeader}</th>
										<th class="pb-1 font-medium">{copy.statusHeader}</th>
									</tr>
								</thead>
								<tbody>
									{#each reasoning.values_referenced as value, index (valueKey(value, index))}
										<tr class="border-b border-border/40">
											<td class="py-1 pr-3 text-foreground">{value.name}</td>
											<td class="py-1 pr-3 text-foreground">
												{value.value}{value.unit ? ` ${value.unit}` : ''}
											</td>
											<td class="py-1 pr-3 text-muted-foreground">
												{value.ref_low != null && value.ref_high != null
													? `${value.ref_low}–${value.ref_high}`
													: '—'}
											</td>
											<td class={`py-1 font-medium ${statusClass(value.status)}`}>
												{statusLabel(value.status)}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						{/if}

						{#if reasoning.uncertainty_flags.length > 0}
							<ul class="mb-3 space-y-0.5 text-[12px] text-muted-foreground">
								{#each reasoning.uncertainty_flags as flag, index (flagKey(flag, index))}
									<li class="flex items-start gap-1">
										<span aria-hidden="true">⚠</span>
										<span>{flag}</span>
									</li>
								{/each}
							</ul>
						{/if}

						{#if reasoning.prior_documents_referenced.length > 0}
							<p class="text-[12px] text-muted-foreground">
								{copy.priorDocumentsReferenced}
								{reasoning.prior_documents_referenced.join(', ')}
							</p>
						{/if}
					{/if}
				</div>
			{/if}
			<p class="text-[11px] text-muted-foreground">
				{copy.disclaimer}
			</p>
		</section>
	{/if}
</div>
{#if interpretationQuery.isPending}
	<div
		aria-busy="true"
		aria-label={copy.loadingAria}
		class="animate-pulse rounded-lg h-32 bg-card border border-border"
	></div>
{:else if interpretationQuery.isError && !is404(interpretationQuery.error)}
	<p class="text-[13px] text-muted-foreground">{copy.cardInterpretationUnavailable}</p>
{/if}
