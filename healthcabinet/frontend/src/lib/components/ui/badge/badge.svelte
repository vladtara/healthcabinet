<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	type Variant = 'default' | 'info' | 'success' | 'warning' | 'danger';

	interface Props extends HTMLAttributes<HTMLSpanElement> {
		children?: Snippet;
		variant?: Variant;
	}

	let { children, class: className, variant = 'default', ...rest }: Props = $props();
	let classes = $derived(`hc-badge hc-badge-${variant} ${className ?? ''}`.trim());
</script>

<span class={classes} {...rest}>
	{@render children?.()}
</span>
