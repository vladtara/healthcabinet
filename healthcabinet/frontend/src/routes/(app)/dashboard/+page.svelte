<script lang="ts">
	import { goto } from '$app/navigation';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { getDashboardInterpretation } from '$lib/api/ai';
	import { listDocuments } from '$lib/api/documents';
	import { Button } from '$lib/components/ui/button';
	import { getDashboardBaseline, getHealthValues } from '$lib/api/health-values';
	import type { HealthValue } from '$lib/api/health-values';
	import { getProfile } from '$lib/api/users';
	import PatientSummaryBar from '$lib/components/health/PatientSummaryBar.svelte';
	import BiomarkerTable from '$lib/components/health/BiomarkerTable.svelte';
	import AIClinicalNote from '$lib/components/health/AIClinicalNote.svelte';
	import AIChatWindow from '$lib/components/health/AIChatWindow.svelte';
	import type { Document } from '$lib/types/api';
	import { authStore } from '$lib/stores/auth.svelte';
	import { statusBarStore } from '$lib/stores/status-bar.svelte';
	import {
		dashboardFilterStore,
		type DashboardFilter
	} from '$lib/stores/dashboard-filter.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { formatDate } from '$lib/i18n/format';
	import { selectPlural } from '$lib/i18n/plural';
	import {
		translateFrequency,
		translateRationale,
		translateTestName
	} from '$lib/i18n/recommendation-catalog';

	const copy = $derived(t(localeStore.locale).dashboard);

	const queryClient = useQueryClient();
	const FILTER_OPTIONS: DashboardFilter[] = ['all', 'analysis', 'document'];

	const filter = $derived<DashboardFilter>(dashboardFilterStore.filter);

	const valuesQuery = createQuery(() => ({
		queryKey: ['health_values', filter] as const,
		queryFn: () => getHealthValues(filter),
		// Keep the prior filter's rows visible while the new filter's fetch is
		// in flight so the filter radio (and rest of the active branch) doesn't
		// get replaced by the loading skeleton on every filter switch.
		placeholderData: (prev: HealthValue[] | undefined) => prev
	}));

	const documentsQuery = createQuery(() => ({
		queryKey: ['documents'] as const,
		queryFn: listDocuments
	}));

	const baselineQuery = createQuery(() => ({
		queryKey: ['baseline'] as const,
		queryFn: getDashboardBaseline
	}));

	const profileQuery = createQuery(() => ({
		queryKey: ['profile'] as const,
		queryFn: getProfile
	}));

	const values = $derived<HealthValue[]>(valuesQuery.data ?? []);
	const documents = $derived<Document[]>(documentsQuery.data ?? []);
	const recommendations = $derived(baselineQuery.data?.recommendations ?? []);
	const loading = $derived(valuesQuery.isPending || documentsQuery.isPending || baselineQuery.isPending);
	const error = $derived(
		valuesQuery.isError || documentsQuery.isError || baselineQuery.isError
			? copy.loadErrorBody
			: null
	);

	function matchesDashboardFilter(document: Document, activeFilter: DashboardFilter): boolean {
		if (document.document_kind === 'unknown') return false;
		if (activeFilter === 'all') return document.document_kind === 'analysis' || document.document_kind === 'document';
		return document.document_kind === activeFilter;
	}

	function errorStatus(error: unknown): number | null {
		const status = (error as { status?: number } | null)?.status;
		return typeof status === 'number' ? status : null;
	}

	const filteredDocuments = $derived(
		documents.filter((document) => matchesDashboardFilter(document, filter))
	);

	const dashboardInterpretationQuery = createQuery(() => ({
		queryKey: ['ai_dashboard_interpretation', filter] as const,
		queryFn: () => getDashboardInterpretation(filter),
		enabled: filteredDocuments.length > 0,
		retry: false
	}));

	// Group existing values by canonical biomarker name for inline sparklines (no extra API calls)
	const timelineByBiomarker = $derived(
		Object.fromEntries(
			[...new Set(values.map((v) => v.canonical_biomarker_name))].map((name) => [
				name,
				values
					.filter((v) => v.canonical_biomarker_name === name)
					.sort(
						(a, b) =>
							new Date(a.measured_at ?? a.created_at).getTime() -
							new Date(b.measured_at ?? b.created_at).getTime()
					)
			])
		)
	);

	// Unique canonical biomarker names for the trend section
	const uniqueBiomarkers = $derived([...new Set(values.map((v) => v.canonical_biomarker_name))]);

	// PatientSummaryBar derived props — filtered dataset, not the whole account
	const userEmail = $derived(authStore.user?.email ?? '');
	const documentCount = $derived(filteredDocuments.length);

	// Whether the user has ANY documents (across all filters). We detect this
	// by looking at the baseline endpoint which exposes has_uploads, so we can
	// distinguish "zero total documents" (first-time) from "zero under the
	// active filter" (filter-empty) without a second fetch.
	const hasAnyDocuments = $derived<boolean>(baselineQuery.data?.has_uploads === true);
	const hasFilteredDocuments = $derived(filteredDocuments.length > 0);
	const filterHasValues = $derived(values.length > 0);
	// Tri-state signal: false = "confirmed empty" (skip AI round-trip; disable
	// Send); true = "confirmed populated"; undefined = "still resolving"
	// (children treat this as pending: AIClinicalNote runs the query / shows
	// skeleton, AIChatWindow disables Send until resolution — see 15.3 review).
	const dashboardHasContext = $derived.by((): boolean | undefined => {
		if (!hasFilteredDocuments) return false;
		if (dashboardInterpretationQuery.data) return true;
		if (errorStatus(dashboardInterpretationQuery.error) === 409) return false;
		return undefined;
	});

	const latestFilteredDocument = $derived.by(() => {
		if (filteredDocuments.length === 0) return null;
		return filteredDocuments.reduce((latest, current) =>
			current.created_at > latest.created_at ? current : latest
		);
	});

	$effect(() => {
		if (!loading && !error) {
			const fields: string[] = [];
			const docsLabel = selectPlural(localeStore.locale, documentCount, {
				one: copy.statusFieldDocumentsOne,
				few: copy.statusFieldDocumentsFew,
				many: copy.statusFieldDocumentsMany,
				other: copy.statusFieldDocumentsOther
			});
			fields.push(`${documentCount} ${docsLabel}`);
			const bmLabel = selectPlural(localeStore.locale, uniqueBiomarkers.length, {
				one: copy.statusFieldBiomarkersOne,
				few: copy.statusFieldBiomarkersFew,
				many: copy.statusFieldBiomarkersMany,
				other: copy.statusFieldBiomarkersOther
			});
			fields.push(`${uniqueBiomarkers.length} ${bmLabel}`);
			if (latestFilteredDocument) {
				const date = formatDate(latestFilteredDocument.created_at, localeStore.locale);
				fields.push(`${copy.statusFieldLastImport}: ${date}`);
			}
			// Sentinel 'Ready' stays stable; AppShell renders the localized label.
			statusBarStore.set('Ready', fields);
		}
	});

	function retry() {
		queryClient.invalidateQueries({ queryKey: ['documents'] });
		queryClient.invalidateQueries({ queryKey: ['health_values'] });
		queryClient.invalidateQueries({ queryKey: ['baseline'] });
		queryClient.invalidateQueries({ queryKey: ['timeline'] });
		queryClient.invalidateQueries({ queryKey: ['ai_dashboard_interpretation'] });
	}

	function filterEmptyCopy(f: DashboardFilter): string {
		switch (f) {
			case 'analysis':
				return copy.emptyAnalysis;
			case 'document':
				return copy.emptyDocument;
			default:
				return copy.emptyAll;
		}
	}

	function biomarkerEmptyCopy(f: DashboardFilter): string {
		if (f === 'document') {
			return copy.biomarkerEmptyDocument;
		}
		return copy.biomarkerEmptyDefault;
	}

	function onFilterChange(next: DashboardFilter) {
		dashboardFilterStore.setFilter(next);
	}
</script>

<div>
	{#if !loading && !error}
		<PatientSummaryBar
			email={userEmail}
			profile={profileQuery.data ?? null}
			{documentCount}
			biomarkerCount={uniqueBiomarkers.length}
		/>
	{/if}

	{#if loading}
		<section aria-label={copy.loadingAria} role="status">
			<div class="hc-dash-section">
				<div class="hc-dash-section-body">
					{#each [0, 1, 2] as i}
						<div class="hc-dash-rec-item animate-pulse" aria-hidden="true" data-skeleton={i}>
							<div class="mb-2 h-4 w-2/5 rounded bg-muted"></div>
							<div class="mb-1 h-3 w-4/5 rounded bg-muted"></div>
							<div class="h-3 w-1/3 rounded bg-muted"></div>
						</div>
					{/each}
				</div>
			</div>
			<span class="sr-only">{copy.loadingText}</span>
		</section>
	{:else if error}
		<div class="hc-dash-section">
			<div class="hc-dash-section-body" style="text-align: center;">
				<div role="alert">
					<p class="mb-4 text-sm text-destructive">{error}</p>
				</div>
				<Button variant="standard" onclick={retry}>{copy.errorRetry}</Button>
			</div>
		</div>
		{:else if hasAnyDocuments}
			<div class="hc-action-bar">
				<fieldset
					class="hc-dash-filter"
					aria-label={copy.filterAria}
					data-testid="dashboard-filter"
				>
					<legend class="sr-only">{copy.filterLegend}</legend>
					{#each FILTER_OPTIONS as opt}
						<label>
							<input
								type="radio"
								name="dashboard-filter"
							value={opt}
							checked={filter === opt}
							onchange={() => onFilterChange(opt)}
						/>
						<span>
							{#if opt === 'all'}{copy.filterAll}{:else if opt === 'analysis'}{copy.filterAnalyses}{:else}{copy.filterDocuments}{/if}
						</span>
						</label>
					{/each}
				</fieldset>
				<button onclick={() => goto('/documents/upload')}>{copy.importDocument}</button>
			</div>

			{#if hasFilteredDocuments}
				<section aria-label={copy.biomarkersAria}>
					<div class="hc-dash-section">
						{#if filterHasValues}
							<BiomarkerTable {values} {timelineByBiomarker} />
						{:else}
							<div class="hc-dash-section-body" data-testid="dashboard-biomarker-empty">
								<p class="hc-ai-note-empty">{biomarkerEmptyCopy(filter)}</p>
							</div>
						{/if}
					</div>
				</section>

				<!-- AI Clinical Note -->
				<section aria-label={copy.interpretationAria} style="margin-top: 8px;">
					<AIClinicalNote
						mode="dashboard"
						documentKind={filter}
						hasContext={dashboardHasContext}
					/>
				</section>

				<!-- AI Chat Window -->
				<section aria-label={copy.chatAria} style="margin-top: 8px;">
					<AIChatWindow
						mode="dashboard"
						documentKind={filter}
						hasContext={dashboardHasContext}
					/>
				</section>
			{:else}
				<section aria-label={copy.filteredResultsAria}>
					<div class="hc-dash-section">
						<div class="hc-dash-section-body" data-testid="dashboard-filter-empty">
							<p class="hc-ai-note-empty">{filterEmptyCopy(filter)}</p>
						</div>
					</div>
				</section>

				<section aria-label={copy.interpretationAria} style="margin-top: 8px;">
					<AIClinicalNote mode="dashboard" documentKind={filter} hasContext={false} />
				</section>

				<section aria-label={copy.chatAria} style="margin-top: 8px;">
					<AIChatWindow mode="dashboard" documentKind={filter} hasContext={false} />
				</section>
			{/if}
		{:else}
			<!-- First-time empty state: no documents at all -->
			<section aria-label={copy.firstTimeAria}>
			<div class="hc-empty-center">
				<div class="hc-empty-icon" aria-hidden="true">📋</div>
				<div class="hc-empty-title">{copy.firstTimeTitle}</div>
				<div class="hc-empty-sub">{copy.firstTimeSub}</div>
				<button onclick={() => goto('/documents/upload')}>{copy.firstTimeUpload}</button>
				<div class="hc-empty-hint">{copy.firstTimeHint}</div>
			</div>
		</section>

		{#if recommendations.length > 0}
			<section aria-label={copy.baselineAria}>
				<div class="hc-dash-section">
					<div class="hc-dash-section-header">{copy.recommendedTestsHeader}</div>
					<div class="hc-dash-section-body">
						<div class="hc-data-table" style="overflow: auto;">
							<table class="hc-small-table">
								<thead>
									<tr>
										<th>{copy.recommendedTestColumn}</th>
										<th>{copy.recommendedFrequencyColumn}</th>
										<th>{copy.recommendedReasonColumn}</th>
									</tr>
								</thead>
								<tbody>
									{#each recommendations as rec}
										<tr>
											<td>{translateTestName(localeStore.locale, rec.test_name)}</td>
											<td>{translateFrequency(localeStore.locale, rec.frequency)}</td>
											<td>{translateRationale(localeStore.locale, rec.rationale)}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
						<p class="hc-ai-disclaimer">{copy.recommendedDisclaimer}</p>
					</div>
				</div>
			</section>
		{/if}
	{/if}
</div>
