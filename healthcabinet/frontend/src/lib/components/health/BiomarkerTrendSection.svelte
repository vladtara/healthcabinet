<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { getHealthValueTimeline } from '$lib/api/health-values';
	import BiomarkerTrendChart from './BiomarkerTrendChart.svelte';

	interface Props {
		canonicalName: string;
		hasValues: boolean;
	}

	const { canonicalName, hasValues }: Props = $props();

	const trendQuery = createQuery(() => ({
		queryKey: ['timeline', canonicalName] as const,
		queryFn: () => getHealthValueTimeline(canonicalName),
		enabled: hasValues
	}));

	function getTrendDirection(values: { value: number }[]): { label: string; symbol: string; colorClass: string } {
		if (values.length < 2) return { label: 'Not enough data', symbol: '', colorClass: 'hc-trend-direction-stable' };
		const first = values[0].value;
		const last = values[values.length - 1].value;
		if (first === 0) return { label: 'Stable', symbol: '→', colorClass: 'hc-trend-direction-stable' };
		const changePercent = ((last - first) / Math.abs(first)) * 100;
		if (changePercent > 5) return { label: 'Increasing', symbol: '↑', colorClass: 'hc-trend-direction-up' };
		if (changePercent < -5) return { label: 'Decreasing', symbol: '↓', colorClass: 'hc-trend-direction-down' };
		return { label: 'Stable', symbol: '→', colorClass: 'hc-trend-direction-stable' };
	}
</script>

{#if trendQuery.isPending}
	<div class="animate-pulse" aria-hidden="true">
		<div class="hc-trend-header">
			<div class="h-4 w-2/5 rounded bg-muted"></div>
		</div>
		<div style="padding: 12px;">
			<div class="h-32 w-full rounded bg-muted"></div>
		</div>
	</div>
{:else if trendQuery.isError}
	<div>
		<div class="hc-trend-header">
			<h2>{canonicalName}</h2>
		</div>
		<div style="padding: 12px; text-align: center;">
			<p class="text-xs text-muted-foreground">Unable to load trend for {canonicalName}.</p>
		</div>
	</div>
{:else if trendQuery.data}
	{@const latestValue = trendQuery.data.values.at(-1)}
	{@const direction = getTrendDirection(trendQuery.data.values)}
	<div>
		<div class="hc-trend-header">
			<h2>{trendQuery.data.biomarker_name}</h2>
			{#if direction.symbol}
				<span class="hc-trend-direction {direction.colorClass}">
					{direction.symbol} {direction.label}
				</span>
			{/if}
		</div>
		<div style="padding: 12px;">
			<BiomarkerTrendChart
				points={trendQuery.data.values.map((hv) => ({
					date: hv.measured_at ?? hv.created_at,
					value: hv.value,
					unit: hv.unit
				}))}
				biomarkerName={trendQuery.data.biomarker_name}
				referenceRangeLow={latestValue?.reference_range_low ?? null}
				referenceRangeHigh={latestValue?.reference_range_high ?? null}
				unit={latestValue?.unit ?? null}
				latestStatus={latestValue?.status ?? null}
			/>
		</div>
	</div>
{/if}
