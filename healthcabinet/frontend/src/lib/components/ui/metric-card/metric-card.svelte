<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		label: string;
		value: string | number;
		children?: Snippet;
	}

	let { label, value, children, class: className, ...rest }: Props = $props();
	let classes = $derived(`hc-metric-card ${className ?? ''}`.trim());
</script>

<div class={classes} {...rest}>
	<p class="hc-metric-label">{label}</p>
	<p class="hc-metric-value">{value}</p>
	{#if children}
		{@render children()}
	{/if}
</div>
