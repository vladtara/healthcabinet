<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	interface Props extends Omit<HTMLInputAttributes, 'type'> {
		checked?: boolean;
	}

	let { class: className, checked = $bindable(false), ...rest }: Props = $props();
</script>

<input type="checkbox" class="hc-checkbox {className ?? ''}" bind:checked {...rest} />
