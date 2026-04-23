<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		legend?: string;
		direction?: 'horizontal' | 'vertical';
		children?: Snippet;
		class?: string;
		disabled?: boolean;
	}

	let {
		legend,
		direction = 'vertical',
		children,
		class: className = '',
		disabled = false
	}: Props = $props();
</script>

<fieldset class="hc-radio-group hc-radio-group-{direction} {className}" {disabled}>
	{#if legend}
		<legend>{legend}</legend>
	{/if}
	{@render children?.()}
</fieldset>
