<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	let { class: className, value = $bindable(), ...rest }: HTMLInputAttributes = $props();
</script>

<input class="hc-input {className ?? ''}" bind:value {...rest} />
