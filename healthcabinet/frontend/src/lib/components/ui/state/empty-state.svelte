<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		title?: string;
		description?: string;
		icon?: string;
		action?: { label: string; onclick: () => void };
		children?: Snippet;
	}

	let { title, description, icon, action, children, class: className, ...rest }: Props = $props();
	let classes = $derived(`hc-state hc-state-empty ${className ?? ''}`.trim());
</script>

<div class={classes} {...rest}>
	{#if children}
		{@render children()}
	{:else}
		{#if icon}<span class="hc-state-icon">{icon}</span>{/if}
		{#if title}<p class="hc-state-title"><strong>{title}</strong></p>{/if}
		{#if description}<p class="hc-state-description">{description}</p>{/if}
		{#if action}<button type="button" class="hc-button" onclick={action.onclick}
				>{action.label}</button
			>{/if}
	{/if}
</div>
