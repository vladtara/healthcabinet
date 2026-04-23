<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		lines?: number;
		message?: string;
	}

	let { lines = 3, message, class: className, ...rest }: Props = $props();
	let safeLines = $derived(Math.max(1, Math.floor(lines)));
	let classes = $derived(`hc-state hc-state-loading ${className ?? ''}`.trim());

	const widths = [60, 80, 45, 70, 55];
</script>

<div class={classes} aria-busy="true" {...rest}>
	{#if message}
		<p class="hc-state-description" aria-live="polite">{message}</p>
	{/if}
	{#each Array(safeLines) as _, i}
		<div class="hc-skeleton-line" style="width: {widths[i % widths.length]}%"></div>
	{/each}
</div>
