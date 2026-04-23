<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title: string;
		showControls?: boolean;
		onClose?: () => void;
		children?: Snippet;
		class?: string;
	}

	let { title, showControls = false, onClose, children, class: className = '' }: Props = $props();
</script>

<div class="window hc-window {className}">
	<div class="title-bar">
		<div class="title-bar-text">{title}</div>
		{#if showControls}
			<div class="title-bar-controls">
				<button type="button" aria-label="Minimize"></button>
				<button type="button" aria-label="Maximize"></button>
				<button type="button" aria-label="Close" onclick={onClose}></button>
			</div>
		{/if}
	</div>
	<div class="window-body">
		{@render children?.()}
	</div>
</div>
