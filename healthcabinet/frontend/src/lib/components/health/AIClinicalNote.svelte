<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { marked } from 'marked';
	import {
		getDocumentInterpretation,
		getDashboardInterpretation,
		type AiInterpretationResponse,
		type DashboardInterpretationResponse
	} from '$lib/api/ai';
	import type { ApiError } from '$lib/api/client.svelte';
	import type { DashboardFilter } from '$lib/stores/dashboard-filter.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

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
			queryFn: (): Promise<InterpretationData> => getDashboardInterpretation(documentKind, localeStore.locale),
			// When the parent has already determined the filter is empty, skip
			// the network round-trip entirely — it would only 409 and produce
			// log noise on every filter-empty mount.
			enabled: hasContext !== false,
			staleTime: 60_000,
			// Retry once on transient errors (429 rate-limit, 503 unavailable).
			// Do NOT retry on 4xx client errors (409 filter-empty is permanent).
			retry: (failureCount: number, error: unknown) => {
				const status = (error as ApiError)?.status;
				if (typeof status === 'number' && status >= 400 && status < 500) return false;
				return failureCount < 1;
			},
			retryDelay: () => 2000
		};
	});

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
			? (interpretationQuery.data as AiInterpretationResponse | undefined)?.reasoning ?? null
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

{#if props.mode === 'document' && props.documentId == null}
	<div class="hc-ai-note">
		<p class="hc-ai-note-empty">{copy.empty}</p>
	</div>
{:else if props.mode === 'dashboard' && props.hasContext === false}
	<div class="hc-ai-note">
		<p class="hc-ai-note-empty">{copy.emptyDashboard}</p>
	</div>
{:else if interpretationQuery.isPending}
	<div class="hc-ai-note" aria-busy="true" aria-label={copy.loadingAria}>
		<div class="animate-pulse">
			<div class="mb-2 h-4 w-2/5 rounded bg-muted"></div>
			<div class="mb-1 h-3 w-full rounded bg-muted"></div>
			<div class="mb-1 h-3 w-4/5 rounded bg-muted"></div>
			<div class="h-3 w-3/5 rounded bg-muted"></div>
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
		<p class="hc-ai-note-header">{copy.header}</p>
		<p class="text-xs text-muted-foreground">{copy.errorUnable}</p>
	</div>
{:else if interpretationQuery.data}
	{@const data = interpretationQuery.data as
		| AiInterpretationResponse
		| DashboardInterpretationResponse}
	<section class="hc-ai-note" aria-label={copy.aria}>
		<p class="hc-ai-note-header">{copy.header}</p>
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
