<script lang="ts">
	import BiomarkerTable from './BiomarkerTable.svelte';
	import type { HealthValue } from '$lib/api/health-values';

	interface Props {
		values: HealthValue[];
		timelineByBiomarker: Record<string, HealthValue[]>;
	}

	const { values, timelineByBiomarker }: Props = $props();
</script>

<BiomarkerTable {values} {timelineByBiomarker} />
