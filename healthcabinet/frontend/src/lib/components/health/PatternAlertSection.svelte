<script lang="ts">
	import type { PatternObservation } from '$lib/api/ai';

	interface Props {
		patterns: PatternObservation[];
		loading: boolean;
		error: boolean;
	}

	const { patterns, loading, error }: Props = $props();

	function formatDates(dates: string[]): string {
		return dates
			.map((d) => {
				const parsed = new Date(d);
				if (Number.isNaN(parsed.getTime())) return d;
				return parsed.toLocaleDateString('en-US', {
					month: 'short',
					year: 'numeric',
					timeZone: 'UTC'
				});
			})
			.join(', ');
	}
</script>

{#if loading}
	<section aria-label="Loading pattern alerts">
		<div class="hc-dash-section">
			<div class="hc-dash-section-header">
				<span aria-hidden="true">📈</span> Pattern Alerts
			</div>
			<div class="hc-dash-section-body">
				{#each [0, 1] as i}
					<div class="hc-pattern-alert animate-pulse" aria-hidden="true" data-skeleton={i}>
						<div class="bg-muted mb-2 h-4 w-4/5 rounded"></div>
						<div class="bg-muted mb-1 h-3 w-2/5 rounded"></div>
						<div class="bg-muted h-3 w-3/5 rounded"></div>
					</div>
				{/each}
			</div>
		</div>
	</section>
{:else if error}
	<section aria-label="Pattern alerts">
		<div class="hc-dash-section">
			<div class="hc-dash-section-header">
				<span aria-hidden="true">📈</span> Pattern Alerts
			</div>
			<div class="hc-dash-section-body" style="text-align: center;">
				<p class="text-muted-foreground text-xs">Unable to load pattern alerts.</p>
			</div>
		</div>
	</section>
{:else if patterns.length > 0}
	<section aria-label="Pattern alerts">
		<div class="hc-dash-section">
			<div class="hc-dash-section-header">
				<span aria-hidden="true">📈</span> Pattern Alerts
			</div>
			<div class="hc-dash-section-body">
				{#each patterns as pattern}
					<div class="hc-pattern-alert">
						<p class="hc-pattern-alert-desc">{pattern.description}</p>
						{#if pattern.document_dates.length > 0}
							<p class="hc-pattern-alert-dates">{formatDates(pattern.document_dates)}</p>
						{/if}
						<p class="hc-pattern-alert-rec">{pattern.recommendation}</p>
					</div>
				{/each}
			</div>
		</div>
	</section>
{/if}
