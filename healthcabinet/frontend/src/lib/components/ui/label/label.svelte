<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLLabelAttributes } from 'svelte/elements';

	interface Props extends HTMLLabelAttributes {
		children?: Snippet;
	}

	let { children, class: className, for: htmlFor, ...rest }: Props = $props();
</script>

<label for={htmlFor} class="hc-label {className ?? ''}" {...rest}>
	{@render children?.()}
</label>
