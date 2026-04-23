<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLSelectAttributes } from 'svelte/elements';

	interface Props extends HTMLSelectAttributes {
		children?: Snippet;
		value?: string;
	}

	let { children, class: className, value = $bindable(), ...rest }: Props = $props();
</script>

<select class="hc-select {className ?? ''}" bind:value {...rest}>
	{@render children?.()}
</select>
