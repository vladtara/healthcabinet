<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		title: string;
		description?: string;
		icon?: string;
	}

	let { title, description, icon = '✓', class: className, ...rest }: Props = $props();
	let classes = $derived(`hc-state hc-state-success ${className ?? ''}`.trim());
</script>

<div class={classes} role="status" {...rest}>
	<p class="hc-state-title"><strong><span class="hc-state-icon">{icon}</span> {title}</strong></p>
	{#if description}<p class="hc-state-description">{description}</p>{/if}
</div>
