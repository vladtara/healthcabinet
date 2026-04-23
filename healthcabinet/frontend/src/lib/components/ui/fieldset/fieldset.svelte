<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		legend?: string;
		children?: Snippet;
		class?: string;
		disabled?: boolean;
	}

	let { legend, children, class: className = '', disabled = false }: Props = $props();
</script>

<fieldset class="hc-fieldset {className}" {disabled}>
	{#if legend}
		<legend>{legend}</legend>
	{/if}
	{@render children?.()}
</fieldset>
