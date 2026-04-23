<script lang="ts">
	interface Props {
		status: 'optimal' | 'borderline' | 'concerning' | 'action_needed' | 'unknown';
	}

	const { status }: Props = $props();

	const CONFIG = {
		optimal: { label: 'Optimal', classes: 'bg-[#2E8B57]/15 text-[#2E8B57]' },
		borderline: { label: 'Borderline', classes: 'bg-[#DAA520]/15 text-[#DAA520]' },
		concerning: { label: 'Concerning', classes: 'bg-[#E07020]/15 text-[#E07020]' },
		action_needed: { label: 'Action needed', classes: 'bg-[#CC3333]/15 text-[#CC3333]' },
		unknown: { label: 'Unknown', classes: 'bg-muted text-muted-foreground' }
	} as const;

	const config = $derived(CONFIG[status] ?? CONFIG.unknown);
</script>

<span
	role="img"
	aria-label="{config.label} status"
	class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {config.classes}"
>
	{config.label}
</span>
