<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { goto } from '$app/navigation';
	import { getAdminMetrics } from '$lib/api/admin';
	import { MetricCard } from '$lib/components/ui/metric-card';

	const queryClient = useQueryClient();

	const metricsQuery = createQuery(() => ({
		queryKey: ['admin', 'metrics'],
		queryFn: getAdminMetrics,
		// Story 5.1 requires metrics to refresh on initial load and explicit user action only.
		refetchOnWindowFocus: false,
		refetchOnReconnect: false
	}));

	function formatRate(rate: number | null | undefined): string {
		if (rate === null || rate === undefined) return 'N/A';
		return `${(rate * 100).toFixed(1)}%`;
	}

	function handleRefresh() {
		queryClient.invalidateQueries({ queryKey: ['admin', 'metrics'] });
	}
</script>

<div class="hc-admin-overview-page">
	<header class="hc-admin-overview-header">
		<h1 class="hc-admin-overview-title">Platform Metrics</h1>
		<button type="button" onclick={handleRefresh} class="btn-standard" aria-label="Refresh metrics">
			Refresh
		</button>
	</header>

	{#if metricsQuery.isPending}
		<div role="status" aria-label="Loading metrics" class="hc-admin-overview-skeleton">
			{#each Array(5) as _}
				<div class="hc-admin-overview-skeleton-card"></div>
			{/each}
		</div>
	{:else if metricsQuery.isError}
		<div class="hc-state hc-state-error">
			<div role="alert">
				<p class="hc-state-title">Unable to load platform metrics.</p>
				<p class="hc-state-description">
					Try refreshing the page or contact support if the issue persists.
				</p>
			</div>
			<button type="button" onclick={handleRefresh} class="btn-standard"> Try again </button>
		</div>
	{:else if metricsQuery.data}
		{@const metrics = metricsQuery.data}
		<div class="hc-admin-overview-stats">
			<MetricCard label="Total Signups" value={metrics.total_signups} />
			<MetricCard label="Total Uploads" value={metrics.total_uploads} />
			<MetricCard label="Upload Success Rate" value={formatRate(metrics.upload_success_rate)} />
			<MetricCard label="Error / Partial Documents" value={metrics.documents_error_or_partial} />
			<MetricCard
				label="AI Interpretation Rate"
				value={formatRate(metrics.ai_interpretation_completion_rate)}
			/>
		</div>

		<div class="hc-admin-overview-sections">
			<fieldset class="hc-fieldset">
				<legend>User Management</legend>
				<p class="hc-admin-overview-section-desc">
					View accounts, manage suspension, and review flagged values.
				</p>
				<div class="hc-admin-overview-section-action">
					<button
						type="button"
						class="btn-standard"
						aria-label="Open User Management"
						onclick={() => goto('/admin/users')}
					>
						Open ->
					</button>
				</div>
			</fieldset>

			<fieldset class="hc-fieldset">
				<legend>Extraction Error Queue</legend>
				<p class="hc-admin-overview-section-desc">
					Review and correct documents with extraction problems.
				</p>
				<div class="hc-admin-overview-section-action">
					<button
						type="button"
						class="btn-standard"
						aria-label="Open Extraction Error Queue"
						onclick={() => goto('/admin/documents')}
					>
						Open ->
					</button>
				</div>
			</fieldset>
		</div>
	{/if}
</div>
