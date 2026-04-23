<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'raised' | 'sunken';
		children?: Snippet;
		class?: string;
	}

	let { variant = 'sunken', children, class: className = '' }: Props = $props();
</script>

<div class="hc-panel hc-panel-{variant} {className}">
	{@render children?.()}
</div>
