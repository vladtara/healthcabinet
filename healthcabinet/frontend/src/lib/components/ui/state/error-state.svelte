<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		title: string;
		description?: string;
		icon?: string;
		action?: { label: string; onclick: () => void };
	}

	let { title, description, icon = '!', action, class: className, ...rest }: Props = $props();
	let classes = $derived(`hc-state hc-state-error ${className ?? ''}`.trim());
</script>

<div class={classes} role="alert" {...rest}>
	<p class="hc-state-title"><strong><span class="hc-state-icon">{icon}</span> {title}</strong></p>
	{#if description}<p class="hc-state-description">{description}</p>{/if}
	{#if action}<button type="button" class="hc-button" onclick={action.onclick}>{action.label}</button>{/if}
</div>
