<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';

	type Status = 'optimal' | 'borderline' | 'concerning' | 'action';

	const statusLabels: Record<Status, string> = {
		optimal: 'Optimal',
		borderline: 'Borderline',
		concerning: 'Concerning',
		action: 'Action needed'
	};

	interface Props extends HTMLAttributes<HTMLDivElement> {
		label: string;
		value: string | number;
		status?: Status;
	}

	let { label, value, status, class: className, ...rest }: Props = $props();
	let classes = $derived(`hc-status-row ${className ?? ''}`.trim());
</script>

<div class={classes} {...rest}>
	<span class="hc-status-row-label">{label}</span>
	<span class="hc-status-row-value">
		{#if status}
			<span class="hc-status-dot hc-status-dot-{status}" aria-hidden="true"></span>
			<span class="hc-status-text">{statusLabels[status]}</span>
		{/if}
		{value}
	</span>
</div>
