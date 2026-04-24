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
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
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
			class="bg-card/50 rounded-md border-l-4 border-l-[#3366FF] p-4"
		>
			<h3 class="text-foreground mb-3 text-base font-semibold">{copy.cardHeader}</h3>
			<div class="text-foreground mb-4 text-[15px] leading-relaxed">
				{interpretationQuery.data.interpretation}
			</div>
			{#if interpretationQuery.data.reasoning}
				<button
					type="button"
					class="mt-3 text-[13px] text-[#3366FF] hover:underline focus-visible:ring-2 focus-visible:ring-[#3366FF] focus-visible:outline-none"
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
									<tr class="border-border text-muted-foreground border-b text-left">
										<th class="pr-3 pb-1 font-medium">{copy.biomarkerHeader}</th>
										<th class="pr-3 pb-1 font-medium">{copy.valueHeader}</th>
										<th class="pr-3 pb-1 font-medium">{copy.referenceRangeHeader}</th>
										<th class="pb-1 font-medium">{copy.statusHeader}</th>
									</tr>
								</thead>
								<tbody>
									{#each reasoning.values_referenced as value, index (valueKey(value, index))}
										<tr class="border-border/40 border-b">
											<td class="text-foreground py-1 pr-3">{value.name}</td>
											<td class="text-foreground py-1 pr-3">
												{value.value}{value.unit ? ` ${value.unit}` : ''}
											</td>
											<td class="text-muted-foreground py-1 pr-3">
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
							<ul class="text-muted-foreground mb-3 space-y-0.5 text-[12px]">
								{#each reasoning.uncertainty_flags as flag, index (flagKey(flag, index))}
									<li class="flex items-start gap-1">
										<span aria-hidden="true">⚠</span>
										<span>{flag}</span>
									</li>
								{/each}
							</ul>
						{/if}

						{#if reasoning.prior_documents_referenced.length > 0}
							<p class="text-muted-foreground text-[12px]">
								{copy.priorDocumentsReferenced}
								{reasoning.prior_documents_referenced.join(', ')}
							</p>
						{/if}
					{/if}
				</div>
			{/if}
			<p class="text-muted-foreground text-[11px]">
				{copy.disclaimer}
			</p>
		</section>
	{/if}
</div>
{#if interpretationQuery.isPending}
	<div
		aria-busy="true"
		aria-label={copy.loadingAria}
		class="bg-card border-border h-32 animate-pulse rounded-lg border"
	></div>
{:else if interpretationQuery.isError && !is404(interpretationQuery.error)}
	<p class="text-muted-foreground text-[13px]">{copy.cardInterpretationUnavailable}</p>
{/if}
