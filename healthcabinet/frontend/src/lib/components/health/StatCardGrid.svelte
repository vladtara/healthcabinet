<script lang="ts">
	interface StatCounts {
		optimal: number;
		borderline: number;
		concerning: number;
		action_needed: number;
	}

	interface Props {
		counts?: Partial<StatCounts> | null;
	}

	const { counts = null }: Props = $props();

	function normalizeCount(value: number | undefined): number {
		if (typeof value !== 'number' || !Number.isFinite(value)) {
			return 0;
		}
		return Math.max(0, Math.trunc(value));
	}

	const safeCounts = $derived({
		optimal: normalizeCount(counts?.optimal),
		borderline: normalizeCount(counts?.borderline),
		concerning: normalizeCount(counts?.concerning),
		action_needed: normalizeCount(counts?.action_needed)
	});

	const statCards = $derived([
		{
			key: 'optimal',
			label: 'Optimal',
			count: safeCounts.optimal,
			cardClass: 'hc-stat-card-optimal'
		},
		{
			key: 'borderline',
			label: 'Borderline',
			count: safeCounts.borderline,
			cardClass: 'hc-stat-card-borderline'
		},
		{
			key: 'concerning',
			label: 'Concerning',
			count: safeCounts.concerning,
			cardClass: 'hc-stat-card-concerning'
		},
		{
			key: 'action-needed',
			label: 'Action Needed',
			count: safeCounts.action_needed,
			cardClass: 'hc-stat-card-action'
		}
	]);
</script>

<section class="hc-stat-grid" aria-label="Biomarker status summary">
	{#each statCards as card (card.key)}
		<article class={`hc-stat-card ${card.cardClass}`} aria-label={`${card.label}: ${card.count}`}>
			<p class="hc-stat-card-count">{card.count}</p>
			<p class="hc-stat-card-label">{card.label}</p>
		</article>
	{/each}
</section>
