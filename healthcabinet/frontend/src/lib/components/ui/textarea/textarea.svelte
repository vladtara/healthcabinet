<script lang="ts">
	import type { HTMLTextareaAttributes } from 'svelte/elements';

	let { class: className, value = $bindable(), ...rest }: HTMLTextareaAttributes = $props();
</script>

<textarea class="hc-textarea {className ?? ''}" bind:value {...rest}></textarea>
