<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	type Props = Omit<HTMLInputAttributes, 'type'>;

	let { class: className, ...rest }: Props = $props();
</script>

<input type="radio" class="hc-radio {className ?? ''}" {...rest} />
