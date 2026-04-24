<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { marked } from 'marked';
	import {
		getDocumentInterpretation,
		getDashboardInterpretation,
		regenerateDashboardInterpretation,
		type AiInterpretationResponse,
		type DashboardInterpretationResponse
	} from '$lib/api/ai';
	import type { ApiError } from '$lib/api/client.svelte';
	import type { DashboardFilter } from '$lib/stores/dashboard-filter.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const queryClient = useQueryClient();

	const copy = $derived(t(localeStore.locale).aiClinicalNote);

	marked.setOptions({ breaks: true, gfm: true });

	type Props =
		| { mode: 'document'; documentId: string | null }
		| { mode: 'dashboard'; documentKind: DashboardFilter; hasContext?: boolean };

	const props: Props = $props();

	let showReasoning = $state(false);

	// Reset expanded-reasoning panel whenever the bound identity flips.
	$effect(() => {
		if (props.mode === 'document') {
			void props.documentId;
		} else {
			void props.documentKind;
		}
		showReasoning = false;
	});

	type InterpretationData = AiInterpretationResponse | DashboardInterpretationResponse;

	const interpretationQuery = createQuery<InterpretationData>(() => {
		if (props.mode === 'document') {
			const documentId = props.documentId;
			return {
				queryKey: ['ai_interpretation', documentId],
				queryFn: (): Promise<InterpretationData> => getDocumentInterpretation(documentId!),
				enabled: documentId != null,
				retry: false
			};
		}
		const documentKind = props.documentKind;
		const hasContext = props.hasContext;
		return {
			queryKey: ['ai_dashboard_interpretation', documentKind, localeStore.locale],
			queryFn: (): Promise<InterpretationData> =>
				getDashboardInterpretation(documentKind, localeStore.locale),
			// When the parent has already determined the filter is empty, skip
			// the network round-trip entirely — it would only 409 and produce
			// log noise on every filter-empty mount.
			enabled: hasContext !== false,
			// The backend now serves the overall note from the ai_memories cache
			// row — GET is a cheap DB read, not an LLM call. Staleness is
			// driven server-side (doc upload / delete / regenerate), so we let
			// TanStack Query keep whatever it has instead of background-
			// refetching after a minute.
			staleTime: Infinity,
			// Retry once on transient errors (429 rate-limit, 503 unavailable).
			// Do NOT retry on 409 filter-empty responses; one retry is allowed for 429.
			retry: (failureCount: number, error: unknown) => {
				const status = (error as ApiError)?.status;
				if (status === 409) return false;
				return failureCount < 1;
			},
			retryDelay: () => 2000
		};
	});

	let isRegenerating = $state(false);

	async function handleRegenerate() {
		if (props.mode === 'document') {
			// Per-document notes are already cached DB rows with no force-regen
			// endpoint today; keep the existing refetch behaviour.
			await interpretationQuery.refetch();
			return;
		}
		if (isRegenerating) return;
		isRegenerating = true;
		try {
			const documentKind = props.documentKind;
			const fresh = await regenerateDashboardInterpretation(documentKind, localeStore.locale);
			queryClient.setQueryData(
				['ai_dashboard_interpretation', documentKind, localeStore.locale],
				fresh
			);
		} catch {
			// Error state surfaces through the normal query lifecycle on the next
			// read; no need to duplicate it here.
			await interpretationQuery.refetch();
		} finally {
			isRegenerating = false;
		}
	}

	function errorStatus(error: unknown): number | null {
		const status = (error as ApiError)?.status;
		return typeof status === 'number' ? status : null;
	}

	/** Soft empty: dashboard 409 → "no AI for this filter"; document 404 → "generating". */
	function isSoftEmpty(error: unknown): boolean {
		const status = errorStatus(error);
		if (props.mode === 'dashboard') return status === 409;
		return status === 404;
	}

	/** Anything else that isn't the soft-empty signal is a hard error. */
	function isHardError(error: unknown): boolean {
		return error != null && !isSoftEmpty(error);
	}

	const documentReasoning = $derived(
		props.mode === 'document'
			? ((interpretationQuery.data as AiInterpretationResponse | undefined)?.reasoning ?? null)
			: null
	);

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
				return '';
		}
	}
</script>

{#snippet regenButton()}
	<button
		class="hc-ai-note-regen"
		class:spinning={interpretationQuery.isFetching || isRegenerating}
		aria-label={copy.regenerateAria}
		title={copy.regenerateAria}
		disabled={interpretationQuery.isFetching || isRegenerating}
		onclick={handleRegenerate}><span aria-hidden="true">↺</span></button
	>
{/snippet}

{#if props.mode === 'document' && props.documentId == null}
	<div class="hc-ai-note">
		<p class="hc-ai-note-empty">{copy.empty}</p>
	</div>
{:else if props.mode === 'dashboard' && props.hasContext === false}
	<div class="hc-ai-note">
		<p class="hc-ai-note-empty">{copy.emptyDashboard}</p>
	</div>
{:else if interpretationQuery.isPending || (interpretationQuery.isFetching && !interpretationQuery.data)}
	<div class="hc-ai-note" aria-busy="true" aria-label={copy.loadingAria}>
		<div class="animate-pulse">
			<div class="bg-muted mb-2 h-4 w-2/5 rounded"></div>
			<div class="bg-muted mb-1 h-3 w-full rounded"></div>
			<div class="bg-muted mb-1 h-3 w-4/5 rounded"></div>
			<div class="bg-muted h-3 w-3/5 rounded"></div>
		</div>
	</div>
{:else if interpretationQuery.isError && isSoftEmpty(interpretationQuery.error)}
	<div class="hc-ai-note">
		{#if props.mode === 'dashboard'}
			<p class="hc-ai-note-empty">{copy.emptyDashboard}</p>
		{:else}
			<p class="hc-ai-note-empty">{copy.generating}</p>
		{/if}
	</div>
{:else if interpretationQuery.isError && isHardError(interpretationQuery.error)}
	<div class="hc-ai-note">
		<div class="hc-ai-note-header-row">
			<p class="hc-ai-note-header">{copy.header}</p>
			{@render regenButton()}
		</div>
		<p class="text-muted-foreground text-xs">{copy.errorUnable}</p>
	</div>
{:else if interpretationQuery.data}
	{@const data = interpretationQuery.data as
		| AiInterpretationResponse
		| DashboardInterpretationResponse}
	<section class="hc-ai-note" aria-label={copy.aria}>
		<div class="hc-ai-note-header-row">
			<p class="hc-ai-note-header">{copy.header}</p>
			{@render regenButton()}
		</div>
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		<div class="hc-ai-note-body">{@html marked(data.interpretation)}</div>

		{#if documentReasoning}
			<button
				class="hc-ai-note-toggle"
				aria-expanded={showReasoning}
				aria-controls="ai-note-reasoning"
				onclick={() => {
					showReasoning = !showReasoning;
				}}
			>
				{showReasoning ? copy.reasoningHide : copy.reasoningShow}
			</button>

			{#if showReasoning}
				{@const reasoning = documentReasoning}
				<div id="ai-note-reasoning" class="hc-ai-note-reasoning">
					{#if reasoning.values_referenced.length > 0}
						<table>
							<caption class="sr-only">{copy.reasoningTableCaption}</caption>
							<thead>
								<tr>
									<th>{copy.biomarkerHeader}</th>
									<th>{copy.valueHeader}</th>
									<th>{copy.referenceHeader}</th>
									<th>{copy.statusHeader}</th>
								</tr>
							</thead>
							<tbody>
								{#each reasoning.values_referenced as val}
									<tr>
										<td>{val.name}</td>
										<td>{val.value}{val.unit ? ` ${val.unit}` : ''}</td>
										<td
											>{val.ref_low != null && val.ref_high != null
												? `${val.ref_low}–${val.ref_high}`
												: '—'}</td
										>
										<td class={statusClass(val.status)}>{statusLabel(val.status)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}

					{#if reasoning.uncertainty_flags.length > 0}
						<ul class="mt-2" style="font-size: 12px; color: var(--text-secondary);">
							{#each reasoning.uncertainty_flags as flag}
								<li>⚠ {flag}</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/if}
		{/if}

		<p class="hc-ai-note-disclaimer">
			{copy.disclaimer}
		</p>
	</section>
{/if}
