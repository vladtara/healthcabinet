<script lang="ts">
	import type { HealthValue } from '$lib/api/health-values';

	interface Props {
		values: HealthValue[];
		timelineByBiomarker: Record<string, HealthValue[]>;
	}

	const { values, timelineByBiomarker }: Props = $props();

	let expandedName = $state<string | null>(null);

	// Deduplicate: show one row per canonical biomarker (latest value)
	const biomarkerRows = $derived(() => {
		const seen = new Map<string, HealthValue>();
		for (const v of values) {
			const existing = seen.get(v.canonical_biomarker_name);
			if (!existing || v.created_at > existing.created_at) {
				seen.set(v.canonical_biomarker_name, v);
			}
		}
		return [...seen.values()].sort((a, b) => a.biomarker_name.localeCompare(b.biomarker_name));
	});

	function statusSymbol(status: string): string {
		switch (status) {
			case 'optimal':
				return '●';
			case 'borderline':
				return '⚠';
			case 'concerning':
				return '◆';
			case 'action_needed':
				return '▲';
			default:
				return '—';
		}
	}

	function statusLabel(status: string): string {
		switch (status) {
			case 'optimal':
				return 'Optimal';
			case 'borderline':
				return 'Borderline';
			case 'concerning':
				return 'Concerning';
			case 'action_needed':
				return 'Action';
			default:
				return 'Unknown';
		}
	}

	function statusClass(status: string): string {
		switch (status) {
			case 'optimal':
				return 'hc-v2-status-optimal';
			case 'borderline':
				return 'hc-v2-status-borderline';
			case 'concerning':
				return 'hc-v2-status-concerning';
			case 'action_needed':
				return 'hc-v2-status-action';
			default:
				return '';
		}
	}

	function rowBorderClass(status: string): string {
		switch (status) {
			case 'borderline':
				return 'hc-v2-row-borderline';
			case 'concerning':
				return 'hc-v2-row-concerning';
			case 'action_needed':
				return 'hc-v2-row-action';
			default:
				return '';
		}
	}

	function trendArrow(timeline: HealthValue[] | undefined): string {
		if (!timeline || timeline.length < 2) return '—';
		const first = timeline[0].value;
		const last = timeline[timeline.length - 1].value;
		if (first === 0) return last > 0 ? '↑' : '→';
		const pct = ((last - first) / Math.abs(first)) * 100;
		if (pct > 15) return '↑↑';
		if (pct > 5) return '↑';
		if (pct < -15) return '↓↓';
		if (pct < -5) return '↓';
		return '→';
	}

	function formatRefRange(v: HealthValue): string {
		if (v.reference_range_low == null && v.reference_range_high == null) return '—';
		const lo = v.reference_range_low;
		const hi = v.reference_range_high;
		if (lo != null && hi != null) return `${lo} – ${hi}`;
		if (lo != null) return `> ${lo}`;
		if (hi != null) return `< ${hi}`;
		return '—';
	}

	function formatDate(d: string): string {
		return new Date(d).toLocaleDateString('en-CA'); // YYYY-MM-DD
	}

	function toggleExpand(name: string) {
		expandedName = expandedName === name ? null : name;
	}
</script>

<div class="hc-data-table" style="overflow: auto;">
	<table>
		<thead>
			<tr>
				<th style="width: 30px;"><span class="sr-only">Expand</span></th>
				<th>Biomarker ▼</th>
				<th>Unit</th>
				<th>Last Value</th>
				<th>Ref. Range</th>
				<th>Status</th>
				<th>Trend</th>
				<th>History</th>
			</tr>
		</thead>
		<tbody>
			{#each biomarkerRows() as hv (hv.canonical_biomarker_name)}
				{@const timeline = timelineByBiomarker[hv.canonical_biomarker_name] ?? []}
				{@const isExpanded = expandedName === hv.canonical_biomarker_name}
				{@const arrow = trendArrow(timeline)}
				<tr
					class="hc-row-interactive {rowBorderClass(hv.status)} {isExpanded
						? 'hc-v2-row-expanded'
						: ''}"
					onclick={() => toggleExpand(hv.canonical_biomarker_name)}
					tabindex="0"
					onkeydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							toggleExpand(hv.canonical_biomarker_name);
						}
					}}
				>
					<td class="hc-v2-expand-icon">{isExpanded ? '−' : '+'}</td>
					<td class="hc-v2-biomarker-name">{hv.biomarker_name}</td>
					<td>{hv.unit ?? '—'}</td>
					<td class="hc-v2-latest-value">{hv.value}</td>
					<td>{formatRefRange(hv)}</td>
					<td class={statusClass(hv.status)}>{statusSymbol(hv.status)} {statusLabel(hv.status)}</td>
					<td class="hc-v2-trend-cell">{arrow}</td>
					<td class="hc-v2-sparkline-cell">
						{#if timeline.length > 0}
							<span class="hc-v2-sparkline">
								{#each timeline as point, pi}
									{@const maxVal = Math.max(...timeline.map((t) => t.value))}
									{@const minVal = Math.min(...timeline.map((t) => t.value))}
									{@const range = maxVal - minVal || 1}
									{@const heightPct = ((point.value - minVal) / range) * 70 + 30}
									<span
										class="hc-v2-spark-bar {pi === timeline.length - 1 ? 'hc-v2-spark-active' : ''}"
										style="height: {heightPct}%;"
									></span>
								{/each}
							</span>
							{timeline.length} pt{timeline.length === 1 ? '' : 's'}
						{:else}
							<span style="color: var(--text-disabled);">—</span>
						{/if}
					</td>
				</tr>
				{#if isExpanded && timeline.length > 0}
					<tr class="hc-v2-history-row">
						<td colspan="8">
							<div class="hc-v2-history-panel">
								<table class="hc-v2-history-table">
									<thead>
										<tr>
											<th>Date</th>
											<th>Value</th>
											<th>Status</th>
											<th>Source Document</th>
										</tr>
									</thead>
									<tbody>
										{#each [...timeline].reverse() as point}
											<tr>
												<td>{formatDate(point.measured_at ?? point.created_at)}</td>
												<td class="hc-v2-value-cell">{point.value}</td>
												<td class={statusClass(point.status)}
													>{statusSymbol(point.status)} {statusLabel(point.status)}</td
												>
												<td style="color: var(--text-secondary);"
													>Document {point.document_id.substring(0, 8)}</td
												>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						</td>
					</tr>
				{/if}
			{/each}
		</tbody>
	</table>
</div>
