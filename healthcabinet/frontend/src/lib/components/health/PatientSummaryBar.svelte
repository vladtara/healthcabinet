<script lang="ts">
	import type { UserProfile } from '$lib/types/api';

	interface Props {
		email: string;
		profile: UserProfile | null;
		documentCount: number;
		biomarkerCount: number;
	}

	const { email, profile, documentCount, biomarkerCount }: Props = $props();

	const displayName = $derived(
		profile && email
			? email
					.split('@')[0]
					.replace(/[._-]/g, ' ')
					.replace(/\b\w/g, (c) => c.toUpperCase())
			: email || '—'
	);

	const ageDisplay = $derived(profile?.age ?? '—');

	const sexDisplay = $derived(
		profile?.sex === 'male'
			? 'M'
			: profile?.sex === 'female'
				? 'F'
				: profile?.sex === 'other'
					? 'O'
					: '—'
	);

	const conditions = $derived(profile?.known_conditions ?? []);
	let showConditions = $state(false);
</script>

<div class="hc-summary-bar">
	<span class="hc-summary-label">Patient:</span>
	<span class="hc-summary-patient-name">{displayName}</span>
	<span class="hc-summary-sep">|</span>
	<span class="hc-summary-label">Age:</span>
	<span class="hc-summary-value">{ageDisplay}</span>
	<span class="hc-summary-sep">|</span>
	<span class="hc-summary-label">Sex:</span>
	<span class="hc-summary-value">{sexDisplay}</span>
	<span class="hc-summary-sep">|</span>
	<span class="hc-summary-label">Conditions:</span>
	{#if conditions.length > 0}
		<span
			class="hc-summary-conditions-toggle"
			role="button"
			tabindex="0"
			onclick={() => {
				showConditions = !showConditions;
			}}
			onkeydown={(e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					e.preventDefault();
					showConditions = !showConditions;
				}
			}}
		>
			{conditions.length} ▼
			{#if showConditions}
				<span class="hc-summary-conditions-dropdown">
					{#each conditions as cond}
						{cond}<br />
					{/each}
				</span>
			{/if}
		</span>
	{:else}
		<span class="hc-summary-value">None</span>
	{/if}
	<span class="hc-summary-sep">|</span>
	<span class="hc-summary-label">Documents:</span>
	<span class="hc-summary-value">{documentCount}</span>
	<span class="hc-summary-sep">|</span>
	<span class="hc-summary-label">Biomarkers:</span>
	<span class="hc-summary-value">{biomarkerCount}</span>
</div>
