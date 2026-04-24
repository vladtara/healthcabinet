<script lang="ts">
	interface ChartPoint {
		date: string;
		value: number;
		unit: string | null;
	}

	interface Props {
		points: ChartPoint[];
		referenceRangeLow?: number | null;
		referenceRangeHigh?: number | null;
		unit?: string | null;
		biomarkerName: string;
		variant?: 'full' | 'sparkline';
		latestStatus?: 'optimal' | 'borderline' | 'concerning' | 'action_needed' | 'unknown' | null;
	}

	const {
		points,
		referenceRangeLow = null,
		referenceRangeHigh = null,
		unit = null,
		biomarkerName,
		variant = 'full',
		latestStatus = null
	}: Props = $props();

	const STATUS_COLORS: Record<string, string> = {
		optimal: '#2E8B57',
		borderline: '#DAA520',
		concerning: '#E07020',
		action_needed: '#CC3333',
		unknown: '#3366FF'
	};
	const dotColor = $derived(latestStatus ? (STATUS_COLORS[latestStatus] ?? '#3366FF') : '#3366FF');

	const hasEnoughData = $derived(points.length >= 2);

	// ── Date formatting ───────────────────────────────────────────────────────
	function formatDateLabel(dateStr: string): string {
		const d = new Date(dateStr);
		return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
	}

	function formatDateFull(dateStr: string): string {
		const d = new Date(dateStr);
		return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
	}

	// ── Sparkline (60×20, no axes, no tooltip) ───────────────────────────────
	const sparklineCoords = $derived.by(() => {
		if (points.length < 2) return '';
		const minV = Math.min(...points.map((p) => p.value));
		const maxV = Math.max(...points.map((p) => p.value));
		const range = maxV - minV || 1;
		return points
			.map((p, i) => {
				const x = (i / (points.length - 1)) * 58 + 1;
				const y = 19 - ((p.value - minV) / range) * 18;
				return `${x},${y}`;
			})
			.join(' ');
	});

	// ── Full chart dimensions ─────────────────────────────────────────────────
	const CHART_W = 560;
	const CHART_H = 200;
	const PAD_LEFT = 48;
	const PAD_RIGHT = 16;
	const PAD_TOP = 16;
	const PAD_BOTTOM = 36;
	const PLOT_W = CHART_W - PAD_LEFT - PAD_RIGHT;
	const PLOT_H = CHART_H - PAD_TOP - PAD_BOTTOM;

	// ── Full chart computed values ────────────────────────────────────────────
	const minVal = $derived(points.length > 0 ? Math.min(...points.map((p) => p.value)) : 0);
	const maxVal = $derived(points.length > 0 ? Math.max(...points.map((p) => p.value)) : 1);

	const yRange = $derived.by(() => {
		// Expand range to include reference band if present
		let lo = minVal;
		let hi = maxVal;
		if (referenceRangeLow != null) lo = Math.min(lo, referenceRangeLow);
		if (referenceRangeHigh != null) hi = Math.max(hi, referenceRangeHigh);
		const pad = (hi - lo) * 0.1 || 1;
		return { lo: lo - pad, hi: hi + pad };
	});

	function toX(i: number): number {
		if (points.length <= 1) return PAD_LEFT + PLOT_W / 2;
		return PAD_LEFT + (i / (points.length - 1)) * PLOT_W;
	}

	function toY(v: number): number {
		const r = yRange;
		return PAD_TOP + PLOT_H - ((v - r.lo) / (r.hi - r.lo)) * PLOT_H;
	}

	const polylinePoints = $derived(
		hasEnoughData ? points.map((p, i) => `${toX(i)},${toY(p.value)}`).join(' ') : ''
	);

	// Reference band
	const refBandY1 = $derived(referenceRangeHigh != null ? toY(referenceRangeHigh) : PAD_TOP);
	const refBandY2 = $derived(referenceRangeLow != null ? toY(referenceRangeLow) : PAD_TOP + PLOT_H);
	const refBandHeight = $derived(Math.abs(refBandY2 - refBandY1));
	const refBandTop = $derived(Math.min(refBandY1, refBandY2));
	const showRefBand = $derived(referenceRangeLow != null || referenceRangeHigh != null);

	// Y-axis ticks (4 steps)
	const yTicks = $derived.by(() => {
		const r = yRange;
		const step = (r.hi - r.lo) / 4;
		return Array.from({ length: 5 }, (_, i) => {
			const v = r.lo + step * i;
			return { v, y: toY(v), label: v.toFixed(1) };
		});
	});

	// Date range for figcaption
	const firstDate = $derived(points.length > 0 ? formatDateFull(points[0].date) : '');
	const lastDate = $derived(
		points.length > 0 ? formatDateFull(points[points.length - 1].date) : ''
	);
</script>

{#if variant === 'sparkline'}
	<!-- Inline sparkline: 60×20, no axes, no reference band, no tooltip -->
	<svg
		width="60"
		height="20"
		viewBox="0 0 60 20"
		aria-hidden="true"
		focusable="false"
		class="overflow-visible"
	>
		{#if hasEnoughData}
			<polyline points={sparklineCoords} fill="none" stroke={dotColor} stroke-width="1.5" />
		{/if}
	</svg>
{:else}
	<!-- Full chart -->
	<figure class="w-full">
		{#if hasEnoughData}
			<svg
				viewBox="0 0 {CHART_W} {CHART_H}"
				class="w-full"
				role="img"
				aria-label="{biomarkerName} trend chart from {firstDate} to {lastDate}"
			>
				<!-- Reference range band -->
				{#if showRefBand}
					<rect
						x={PAD_LEFT}
						y={refBandTop}
						width={PLOT_W}
						height={refBandHeight}
						fill="#2E8B57"
						fill-opacity="0.12"
					/>
				{/if}

				<!-- Y-axis ticks and gridlines -->
				{#each yTicks as tick}
					<line
						x1={PAD_LEFT}
						y1={tick.y}
						x2={PAD_LEFT + PLOT_W}
						y2={tick.y}
						stroke="currentColor"
						stroke-opacity="0.08"
						stroke-width="1"
					/>
					<text
						x={PAD_LEFT - 6}
						y={tick.y}
						text-anchor="end"
						dominant-baseline="middle"
						class="fill-muted-foreground text-[10px]"
						font-size="10">{tick.label}</text
					>
				{/each}

				<!-- X-axis date labels -->
				{#each points as p, i}
					{#if i === 0 || i === points.length - 1 || (points.length > 4 && i % Math.floor(points.length / 3) === 0)}
						<text
							x={toX(i)}
							y={CHART_H - PAD_BOTTOM + 14}
							text-anchor="middle"
							class="fill-muted-foreground text-[10px]"
							font-size="10">{formatDateLabel(p.date)}</text
						>
					{/if}
				{/each}

				<!-- Unit label on Y-axis -->
				{#if unit}
					<text
						x={PAD_LEFT - 36}
						y={PAD_TOP + PLOT_H / 2}
						text-anchor="middle"
						dominant-baseline="middle"
						transform="rotate(-90, {PAD_LEFT - 36}, {PAD_TOP + PLOT_H / 2})"
						class="fill-muted-foreground text-[10px]"
						font-size="10">{unit}</text
					>
				{/if}

				<!-- Trend line -->
				<polyline points={polylinePoints} fill="none" stroke={dotColor} stroke-width="2" />

				<!-- Data points with tooltips -->
				{#each points as p, i}
					<circle cx={toX(i)} cy={toY(p.value)} r="4" fill={dotColor}>
						<title>{p.value}{p.unit ? ` ${p.unit}` : ''} — {formatDateFull(p.date)}</title>
					</circle>
				{/each}
			</svg>

			<figcaption class="sr-only">
				{biomarkerName} values from {firstDate} to {lastDate}
			</figcaption>
		{:else}
			<!-- Disabled state: < 2 data points -->
			<div
				class="border-border bg-card relative flex h-[200px] items-center justify-center overflow-hidden rounded-lg border"
			>
				<!-- Decorative static placeholder lines (no real axes) -->
				<svg
					viewBox="0 0 560 200"
					class="absolute inset-0 h-full w-full opacity-20"
					aria-hidden="true"
				>
					{#each [40, 80, 120, 160] as y}
						<line x1="48" y1={y} x2="544" y2={y} stroke="currentColor" stroke-width="1" />
					{/each}
					<line x1="48" y1="16" x2="48" y2="164" stroke="currentColor" stroke-width="1" />
				</svg>
				<div class="relative z-10 px-4 text-center">
					<p class="text-muted-foreground text-sm">Upload another document to unlock trends</p>
				</div>
			</div>
			<figcaption class="sr-only">{biomarkerName} trend chart — not enough data</figcaption>
		{/if}

		<!-- Accessible data table alternative for screen readers -->
		<details class="mt-2">
			<summary class="sr-only">Data table for {biomarkerName}</summary>
			<table>
				<thead>
					<tr><th>Date</th><th>Value</th><th>Unit</th></tr>
				</thead>
				<tbody>
					{#each points as p}
						<tr>
							<td>{formatDateFull(p.date)}</td>
							<td>{p.value}</td>
							<td>{p.unit ?? '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</details>
	</figure>
{/if}
